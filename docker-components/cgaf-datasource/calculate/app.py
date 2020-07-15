import argparse
import json
import os
import io
import psycopg2
import psycopg2.extras
import time
import pickle
import PIL.Image
import numpy as np
import base64
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

def getAskPriceSamples(conn,cur,product,maxSize):
   cur.execute( """
      SELECT ask_prices FROM crypto_gaf.samples WHERE product = %s ORDER BY sample_id desc LIMIT %s
      """,(product,maxSize))
   rows = cur.fetchall()
   return [ x[0] for x in rows ]

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

def getBidPriceSamples(conn,cur,product,maxSize):
   cur.execute( """
      SELECT bid_prices FROM crypto_gaf.samples WHERE product = %s ORDER BY sample_id desc LIMIT %s
      """,(product,maxSize))
   rows = cur.fetchall()
   return [ x[0] for x in rows ]

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

def doUpdate(conn,cur,product,size,midpoint,midpointImages,askPriceImages,bidPriceImages):
   sql = """
      UPDATE crypto_gaf.gafs SET midpoint = %s,midpoint_images = %s,ask_price_images = %s,bid_price_images = %s,size = %s WHERE product = %s 
   """
   cur.execute(sql,(midpoint,midpointImages,askPriceImages,bidPriceImages,size,product))

def main(args):
   postgresUser = "postgres"
   postgresPw = None
   postgresHost = "localhost"
   postgresDb = "postgres"
   sleepInterval = 1
   aggregation = 10
   depth = 5
   if os.environ.get('POSTGRES_USER') != None: postgresUser = os.environ.get('POSTGRES_USER')
   if os.environ.get('POSTGRES_PW') != None: postgresPw = os.environ.get('POSTGRES_PW')
   if os.environ.get('POSTGRES_HOST') != None: postgresHost = os.environ.get('POSTGRES_HOST')
   if os.environ.get('POSTGRES_DB') != None: postgresDb = os.environ.get('POSTGRES_DB')
   if os.environ.get('SLEEP_INTERVAL') != None: sleepInterval = float(os.environ.get('SLEEP_INTERVAL'))
   if args.pg_user != None: postgresUser = args.pg_user
   if args.pg_pw != None: postgresPw = args.pg_pw
   if args.pg_host != None: postgresHost = args.pg_host
   if args.db != None: postgresDb = args.db
   if args.sleep != None: sleepInterval = float(args.sleep)
   try:
      startTime = time.time()
      iterations = 0
      conn = psycopg2.connect(host=postgresHost,dbname=postgresDb,user=postgresUser,password=postgresPw)
      while True:
         cur = conn.cursor()
         gafInfo = getGafInfo(conn,cur)
         for i in range(len(gafInfo)):
            product = gafInfo[i][0]
            maxSize = gafInfo[i][1]
            midpointSamples = getMidpointSamples(conn,cur,product,maxSize)
            askPriceSamples = getAskPriceSamples(conn,cur,product,maxSize)
            bidPriceSamples = getBidPriceSamples(conn,cur,product,maxSize)
            size = len(midpointSamples)
            if size >= 10:
               midpointFields = getMidpointFields(midpointSamples,size)
               askPriceFields = getAskPriceFields(askPriceSamples,size)
               bidPriceFields = getBidPriceFields(bidPriceSamples,size)
               midpointImages = getMidpointImages(midpointFields)
               askPriceImages = getAskPriceImages(askPriceFields)
               bidPriceImages = getBidPriceImages(bidPriceFields)
               doUpdate(conn,cur,product,size,midpointSamples[0],midpointImages,askPriceImages,bidPriceImages)
         conn.commit()
         cur.close()
         currentTime = time.time()
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
parser.add_argument('--db', help="postgres db")
parser.add_argument('--kafka', help="kafka host")
parser.add_argument('--sleep', help="sleep interval in seconds")
parser.add_argument('--fetch', help="number of rows to fetch each interval")
args = parser.parse_args()
main(args)
