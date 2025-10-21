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
from pyts.image import GramianAngularField
from pyts.image import MarkovTransitionField


def sanitize_midpoints(midpoints):
   cleaned = []
   last = 0.0
   if midpoints is None:
      return cleaned
   for value in midpoints:
      if value is None:
         cleaned.append(last)
         continue
      try:
         last = float(value)
      except (TypeError, ValueError):
         cleaned.append(last)
         continue
      cleaned.append(last)
   return cleaned

def sanitize_orderbook(price_samples,size_samples,expected_depth=None):
   price_samples = price_samples or []
   size_samples = size_samples or []
   depth = expected_depth or 0
   for row in price_samples:
      if row:
         depth = max(depth,len(row))
   for row in size_samples:
      if row:
         depth = max(depth,len(row))
   if depth == 0:
      return [],[],0
   total = max(len(price_samples),len(size_samples))
   cleaned_price = []
   cleaned_size = []
   last_price = [0.0]*depth
   last_size = [0.0]*depth
   for idx in range(total):
      price_row = price_samples[idx] if idx < len(price_samples) else None
      size_row = size_samples[idx] if idx < len(size_samples) else None
      price_values = []
      size_values = []
      for depth_index in range(depth):
         value = last_price[depth_index]
         if price_row and depth_index < len(price_row) and price_row[depth_index] is not None:
            try:
               value = float(price_row[depth_index])
            except (TypeError, ValueError):
               value = last_price[depth_index]
         price_values.append(value)
         value = last_size[depth_index]
         if size_row and depth_index < len(size_row) and size_row[depth_index] is not None:
            try:
               value = float(size_row[depth_index])
            except (TypeError, ValueError):
               value = last_size[depth_index]
         size_values.append(value)
      cleaned_price.append(price_values)
      cleaned_size.append(size_values)
      last_price = price_values
      last_size = size_values
   return cleaned_price,cleaned_size,depth

def sanitize_trades(trade_samples,expected_len=3):
   trade_samples = trade_samples or []
   cleaned = []
   last = [0.0]*expected_len
   for row in trade_samples:
      values = []
      for idx in range(expected_len):
         value = last[idx]
         if row and idx < len(row) and row[idx] is not None:
            try:
               value = float(row[idx])
            except (TypeError, ValueError):
               value = last[idx]
         values.append(value)
      cleaned.append(values)
      last = values
   if len(cleaned) == 0:
      cleaned.append(last)
   return cleaned

def ensure_length(series,target,template):
   series = series or []
   result = []
   for item in series:
      if isinstance(item,(list,tuple)):
         result.append(list(item))
      else:
         result.append(item)
   if len(result) == 0:
      result.append(template())
   last = result[-1]
   while len(result) < target:
      result.append(list(last) if isinstance(last,list) else last)
   if len(result) > target:
      result = result[:target]
   return result

def trim_depth(series,depth):
   trimmed = []
   for row in series:
      trimmed.append([ float(x) for x in row[:depth] ])
   return trimmed

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
   if postgresPw is None and os.path.exists('/run/secrets/pg_pw'):
      with open('/run/secrets/pg_pw') as secret:
         postgresPw = secret.read().strip()
   try:
      startTime = time.time()
      iterations = 0
      conn = psycopg.connect(host=postgresHost, port=postgresPort, dbname=postgresDb, user=postgresUser, password=postgresPw)
      summaryWindow = 60
      summaryLast = time.time()
      summaryUpdates = 0
      while True:
         cur = conn.cursor()
         gafInfo = getGafInfo(conn,cur)
         for i in range(len(gafInfo)):
            product = gafInfo[i][0]
            maxSize = gafInfo[i][1]
            midpointSamples = sanitize_midpoints(getMidpointSamples(conn,cur,product,maxSize))
            if len(midpointSamples) < 21:
               continue
            askPriceSamples,askSizeSamples,askDepth = sanitize_orderbook(*getAskSamples(conn,cur,product,maxSize))
            bidPriceSamples,bidSizeSamples,bidDepth = sanitize_orderbook(*getBidSamples(conn,cur,product,maxSize))
            buySamples,sellSamples = getBuyAndSellSamples(conn,cur,product,maxSize)
            buySamples = sanitize_trades(buySamples)
            sellSamples = sanitize_trades(sellSamples)
            if not askPriceSamples or not bidPriceSamples:
               continue
            depth = min(askDepth,bidDepth)
            if depth == 0:
               continue
            askPriceSamples = trim_depth(ensure_length(askPriceSamples,len(midpointSamples),lambda: [0.0]*depth),depth)
            askSizeSamples = trim_depth(ensure_length(askSizeSamples,len(midpointSamples),lambda: [0.0]*depth),depth)
            bidPriceSamples = trim_depth(ensure_length(bidPriceSamples,len(midpointSamples),lambda: [0.0]*depth),depth)
            bidSizeSamples = trim_depth(ensure_length(bidSizeSamples,len(midpointSamples),lambda: [0.0]*depth),depth)
            buySamples = ensure_length(buySamples,len(midpointSamples),lambda: [0.0,0.0,0.0])
            sellSamples = ensure_length(sellSamples,len(midpointSamples),lambda: [0.0,0.0,0.0])
            size = len(midpointSamples)
            if size < 21:
               continue
            if not askPriceSamples or not askPriceSamples[0]:
               continue
            try:
               midpointFields = getMidpointFields(midpointSamples,size)
               orderbookField = getOrderbookField(askPriceSamples,askSizeSamples,bidPriceSamples,bidSizeSamples,size)
               buyField = getBuyField(buySamples,size)
               sellField = getSellField(sellSamples,size)
            except (IndexError, ZeroDivisionError) as err:
               print(f"calculate: skipping {product} due to data shape error: {err}")
               continue
            midpointImages = getMidpointImages(midpointFields)
            orderbookImage = fieldToRGB(orderbookField)
            buyImage = fieldToRGB(buyField,permutation=[1,0,2])
            sellImage = fieldToRGB(sellField)
            doUpdate(conn,cur,product,size,midpointSamples[0],midpointImages,orderbookImage,buyImage,sellImage)
            summaryUpdates += 1
         conn.commit()
         cur.close()
         now = time.time()
         if now - summaryLast >= summaryWindow:
            if summaryUpdates > 0:
               print(f"calculate: processed {summaryUpdates} updates in the last {int(now - summaryLast)}s")
               summaryUpdates = 0
            summaryLast = now
         currentTime = now
         iterations = iterations + 1
         sleepTime = startTime + iterations*sleepInterval - currentTime
         if(sleepTime < 0): sleepTime = 0
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
