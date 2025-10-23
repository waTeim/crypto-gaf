import argparse
import json
import os
import io
import psycopg
import time
import pickle
import PIL.Image
import numpy as np
import base64
from concurrent.futures import ThreadPoolExecutor
from pyts.image import GramianAngularField
from pyts.image import MarkovTransitionField

def getGafInfo(conn,cur):
   cur.execute( """
      SELECT product,max_size FROM crypto_gaf.gafs
      """)
   rows = cur.fetchall()
   return [ [x[0],x[1]] for x in rows ]

def getMidpointSamples(conn,cur,product,maxSize):
   cur.execute( """
      SELECT midpoint FROM crypto_gaf.samples WHERE product = %s ORDER BY sample_id desc LIMIT %s
      """,(product,maxSize))
   rows = cur.fetchall()
   return [ x[0] for x in rows ]

def getMidpointFields(samples,size):
   fields = []
   g = GramianAngularField(image_size=size,method='summation')
   S = np.array(samples).reshape(1,size)
   T = g.fit_transform(S)
   fields.append(T[0])
   g = GramianAngularField(image_size=size,method='difference')
   S = np.array(samples).reshape(1,size)
   T = g.fit_transform(S)
   fields.append(T[0])
   return fields

def getMidpointImages(midpointFields):
   images = []
   for i in range(len(midpointFields)):
      scaled = ((midpointFields[i] + 1)/2)*255
      formatted = scaled.astype(np.uint8)
      image = io.BytesIO()
      PIL.Image.fromarray(formatted).save(image,'png')
      images.append(base64.b64encode(image.getvalue()).decode())
   return images

def getAskSamples(conn,cur,product,maxSize):
   cur.execute( """
      SELECT ask_prices,ask_sizes FROM crypto_gaf.samples WHERE product = %s ORDER BY sample_id desc LIMIT %s
      """,(product,maxSize))
   rows = cur.fetchall()
   return [ x[0] for x in rows ],[ x[1] for x in rows ]

def getAskPriceFields(samples,size):
   G = GramianAngularField(image_size=size,method='summation')
   S = np.transpose(np.array(samples))
   T = G.fit_transform(S)
   return T

def getAskPriceImages(askPriceFields):
   images = []
   #for i in range(askPriceFields.shape[0]):
   #   scaled = ((askPriceFields[i] + 1)/2)*255
   #   formatted = scaled.astype(np.uint8)
   #   image = io.BytesIO()
   #   PIL.Image.fromarray(formatted).save(image,'png')
   #   images.append(base64.b64encode(image.getvalue()).decode())
   stack = []
   for i in range(3):
      scaled = ((askPriceFields[i] + 1)/2)*255
      formatted = scaled.astype(np.uint8)
      stack.append(formatted)
   rgb = np.stack(stack,axis=2)
   image = io.BytesIO()
   PIL.Image.fromarray(rgb).save(image,'png')
   images.append(base64.b64encode(image.getvalue()).decode())
   return images

def getBidSamples(conn,cur,product,maxSize):
   cur.execute( """
      SELECT bid_prices,bid_sizes FROM crypto_gaf.samples WHERE product = %s ORDER BY sample_id desc LIMIT %s
      """,(product,maxSize))
   rows = cur.fetchall()
   return [ x[0] for x in rows ],[ x[1] for x in rows ]

def getBidPriceFields(samples,size):
   G = GramianAngularField(image_size=size,method='summation')
   S = np.transpose(np.array(samples))
   T = G.fit_transform(S)
   return T

def getBidPriceImages(bidPriceFields):
   images = []
   stack = []
   for i in range(3):
      scaled = ((bidPriceFields[i] + 1)/2)*255
      formatted = scaled.astype(np.uint8)
      stack.append(formatted)
   rgb = np.stack(stack,axis=2)
   image = io.BytesIO()
   PIL.Image.fromarray(rgb).save(image,'png')
   images.append(base64.b64encode(image.getvalue()).decode())
   return images

def getOrderbookField(askPriceSamples,askSizeSamples,bidPriceSamples,bidSizeSamples,size):
   numSamples = len(askPriceSamples)
   depth = len(askPriceSamples[0])
   samples = []
   for i in range(numSamples):
      samples.append([])
      for j in range(depth): 
         samples[i].append((askPriceSamples[i][j]*askSizeSamples[i][j] - bidPriceSamples[i][j]*bidSizeSamples[i][j])/(askSizeSamples[i][j] + bidSizeSamples[i][j]))
   G = GramianAngularField(image_size=size,method='summation')
   S = np.transpose(np.array(samples))
   T = G.fit_transform(S)
   return T
   
def fieldToRGB(field,permutation=None):
   stack = []
   for i in range(3):
      if permutation != None: index = permutation[i]
      else: index = i
      scaled = ((field[index] + 1)/2)*255
      formatted = scaled.astype(np.uint8)
      stack.append(formatted)
   rgb = np.stack(stack,axis=2)
   image = io.BytesIO()
   PIL.Image.fromarray(rgb).save(image,'png')
   return base64.b64encode(image.getvalue()).decode()

def getBuyAndSellSamples(conn,cur,product,maxSize):
   cur.execute( """
      SELECT 
         avg(buys[1]) over (order by sample_id desc rows between 5 preceding and 5 following),
         avg(buys[2]) over (order by sample_id desc rows between 5 preceding and 5 following),
         avg(buys[3]) over (order by sample_id desc rows between 5 preceding and 5 following),
         avg(sells[1]) over (order by sample_id desc rows between 5 preceding and 5 following),
         avg(sells[2]) over (order by sample_id desc rows between 5 preceding and 5 following),
         avg(sells[3]) over (order by sample_id desc rows between 5 preceding and 5 following)
      FROM crypto_gaf.samples WHERE product = %s ORDER BY sample_id desc LIMIT %s
      """,(product,maxSize))
   rows = cur.fetchall()
   return [ [x[0],x[1],x[2]] for x in rows ],[ [x[3],x[4],x[5]] for x in rows ]

def getBuyField(samples,size):
   G = GramianAngularField(image_size=size,method='summation')
   S = np.transpose(np.array(samples))
   T = G.fit_transform(S)
   return T

def getSellField(samples,size):
   G = GramianAngularField(image_size=size,method='summation')
   S = np.transpose(np.array(samples))
   T = G.fit_transform(S)
   return T

def doUpdate(conn,cur,product,size,midpoint,midpointImages,orderbookImage,buyImage,sellImage):
   sql = """
      UPDATE crypto_gaf.gafs SET midpoint = %s,midpoint_images = %s,orderbook_image = %s,buy_image = %s,sell_image = %s,size = %s WHERE product = %s 
   """
   cur.execute(sql,(midpoint,midpointImages,orderbookImage,buyImage,sellImage,size,product))

def main(args):
   postgresUser = "postgres"
   postgresPw = None
   postgresHost = "postgresql"
   postgresPort = 5432
   postgresDb = "postgres"
   sleepInterval = 1
   aggregation = 10
   depth = 5
   if os.environ.get('POSTGRES_USER') != None: postgresUser = os.environ.get('POSTGRES_USER')
   if os.environ.get('POSTGRES_PW') != None: postgresPw = os.environ.get('POSTGRES_PW')
   if os.environ.get('POSTGRES_HOST') != None: postgresHost = os.environ.get('POSTGRES_HOST')
   if os.environ.get('POSTGRES_PORT') != None: postgresPort = int(os.environ.get('POSTGRES_PORT'))
   if os.environ.get('POSTGRES_DB') != None: postgresDb = os.environ.get('POSTGRES_DB')
   if os.environ.get('SLEEP_INTERVAL') != None: sleepInterval = float(os.environ.get('SLEEP_INTERVAL'))
   if args.pg_user != None: postgresUser = args.pg_user
   if args.pg_pw != None: postgresPw = args.pg_pw
   if args.pg_host != None: postgresHost = args.pg_host
   if args.pg_port != None: postgresPort = int(args.pg_port)
   if args.db != None: postgresDb = args.db
   if args.sleep != None: sleepInterval = float(args.sleep)

   try:
      startTime = time.time()
      iterations = 0
      conn = psycopg.connect(host=postgresHost,dbname=postgresDb,user=postgresUser,password=postgresPw)
      fellBehind = False
      while True:
         cur = conn.cursor()
         gafInfo = getGafInfo(conn,cur)
         for i in range(len(gafInfo)):
            product = gafInfo[i][0]
            maxSize = gafInfo[i][1]
            start_time = time.time()
            midpointSamples = getMidpointSamples(conn,cur,product,maxSize)
            query_midpoint = time.time()
            askPriceSamples,askSizeSamples = getAskSamples(conn,cur,product,maxSize)
            query_ask = time.time()
            bidPriceSamples,bidSizeSamples = getBidSamples(conn,cur,product,maxSize)
            query_bid = time.time()
            buySamples,sellSamples = getBuyAndSellSamples(conn,cur,product,maxSize)
            query_trades = time.time()
            size = len(midpointSamples)
            if size >= 21: 
               with ThreadPoolExecutor(max_workers=4) as executor:
                  future_midpoint = executor.submit(getMidpointFields, midpointSamples, size)
                  future_orderbook = executor.submit(getOrderbookField, askPriceSamples, askSizeSamples, bidPriceSamples, bidSizeSamples, size)
                  future_buy = executor.submit(getBuyField, buySamples, size)
                  future_sell = executor.submit(getSellField, sellSamples, size)
                  midpointFields = future_midpoint.result()
                  orderbookField = future_orderbook.result()
                  buyField = future_buy.result()
                  sellField = future_sell.result()
               midpointImages = getMidpointImages(midpointFields)
               orderbookImage = fieldToRGB(orderbookField)
               buyImage = fieldToRGB(buyField,permutation=[1,0,2])
               sellImage = fieldToRGB(sellField)
               doUpdate(conn,cur,product,size,midpointSamples[0],midpointImages,orderbookImage,buyImage,sellImage)
               calc_done = time.time()
               print(f"calculate timings mid={query_midpoint-start_time:.3f}s ask={query_ask-query_midpoint:.3f}s bid={query_bid-query_ask:.3f}s trades={query_trades-query_bid:.3f}s transforms={calc_done-query_trades:.3f}s")
         conn.commit()
         cur.close()
         currentTime = time.time()
         iterations = iterations + 1
         sleepTime = startTime + iterations*sleepInterval - currentTime
         if sleepTime < 0: sleepTime = 0
         if sleepTime == 0:
            if not fellBehind:
               print('calculate: loop has no idle time; engine may be at capacity')
               fellBehind = True
         else:
            fellBehind = False
         time.sleep(sleepTime)
   except Exception as e:
      print(e)

parser = argparse.ArgumentParser()
parser.add_argument('--pg_user', help="postgres user")
parser.add_argument('--pg_pw', help="postgres password")
parser.add_argument('--pg_host', help="postgres host")
parser.add_argument('--pg_port', help="postgres port")
parser.add_argument('--db', help="postgres db")
parser.add_argument('--kafka', help="kafka host")
parser.add_argument('--sleep', help="sleep interval in seconds")
parser.add_argument('--fetch', help="number of rows to fetch each interval")
args = parser.parse_args()
main(args)
