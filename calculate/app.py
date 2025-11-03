import argparse
import json
import os
import io
import psycopg
import time
import pickle
import traceback
import PIL.Image
import numpy as np
import base64
from concurrent.futures import ThreadPoolExecutor
from pyts.image import GramianAngularField
from pyts.image import MarkovTransitionField

import math

def _clamp01(x):
   return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

def _log_or_none(v):
   return None if v is None or v <= 0 else math.log(v)

def _fit_local_stats(samples):
   vlogs = [_log_or_none(r[1]) for r in samples]
   nlogs = [_log_or_none(r[2]) for r in samples]
   vfinite = [x for x in vlogs if x is not None] or [0.0, 0.0]
   nfinite = [x for x in nlogs if x is not None] or [0.0, 0.0]
   vlo, vhi = min(vfinite), max(vfinite)
   nlo, nhi = min(nfinite), max(nfinite)
   if vhi == vlo: vhi = vlo + 1e-9
   if nhi == nlo: nhi = nlo + 1e-9
   return (vlo, vhi, nlo, nhi)

def fit_shared_stats(buys, sells):
   """
   Build shared log-space min/max from BOTH sides.
   Call once in the main thread; pass to worker threads.
   """
   both = buys + sells
   return _fit_local_stats(both)

def _norm_from_stats(val, lo, hi, fallback=0.5):
   x = _log_or_none(val)
   if x is None:
      return fallback
   return (x - lo) / (hi - lo)

def _apply_contrast(x, n01, cmin, cmax):
   c = cmin + (cmax - cmin) * n01
   return _clamp01(0.5 + c * (x - 0.5))

def samples_to_triplets(
   samples,
   stats=None,                 # optional: (vlo, vhi, nlo, nhi) for shared scaling
   gamma=1.0,
   contrast_range=(0.7, 1.7),
   bg_mode="zero",             # "zero", "floor", "volume", "orders"
   bg_floor=0.05,
   bg_scale=0.2,
):
   """
   One side at a time (buys OR sells).
   Output rows: [primary, bg, bg] in [0,1].
     - primary = volume brightness with orders-driven contrast
     - bg duplicated to preserve pure hue after permutation
   """
   if stats is None:
      stats = _fit_local_stats(samples)
   vlo, vhi, nlo, nhi = stats

   cmin, cmax = contrast_range
   out = []

   for price, vol, ords in samples:
      v01 = _norm_from_stats(vol,  vlo, vhi)
      n01 = _norm_from_stats(ords, nlo, nhi)
      xg = _clamp01(v01) ** gamma
      primary = _apply_contrast(xg, n01, cmin, cmax)

      if bg_mode == "zero":
         bg = 0.0
      elif bg_mode == "floor":
         bg = _clamp01(bg_floor)
      elif bg_mode == "volume":
         bg = _clamp01(v01 * bg_scale)
      elif bg_mode == "orders":
         bg = _clamp01(n01 * bg_scale)
      else:
         bg = 0.0

      out.append([primary, bg, bg])

   return out


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
         denominator = askSizeSamples[i][j] + bidSizeSamples[i][j]
         if denominator == 0:
            samples[i].append(0)
         else:
#            samples[i].append((askPriceSamples[i][j]*askSizeSamples[i][j] - bidPriceSamples[i][j]*bidSizeSamples[i][j])/denominator)
            samples[i].append((bidSizeSamples[i][j] - askSizeSamples[i][j])/denominator)
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
         avg(buys[1]) over (order by sample_id desc rows between 2 preceding and 2 following),
         avg(buys[2]) over (order by sample_id desc rows between 2 preceding and 2 following),
         avg(buys[3]) over (order by sample_id desc rows between 2 preceding and 2 following),
         avg(sells[1]) over (order by sample_id desc rows between 2 preceding and 2 following),
         avg(sells[2]) over (order by sample_id desc rows between 2 preceding and 2 following),
         avg(sells[3]) over (order by sample_id desc rows between 2 preceding and 2 following)
      FROM crypto_gaf.samples WHERE product = %s ORDER BY sample_id desc LIMIT %s
      """,(product,maxSize))
   rows = cur.fetchall()
   return [ [x[0],x[1],x[2]] for x in rows ],[ [x[3],x[4],x[5]] for x in rows ]

def getBuyField(samples,size,stats):
   buy_triplets = samples_to_triplets(samples, stats=stats, bg_mode="zero")
   G = GramianAngularField(image_size=size,method='summation',sample_range=(0, 1))
   S = np.transpose(np.array(buy_triplets))
   T = G.fit_transform(S)
   return T

def getSellField(samples,size,stats):
   sell_triplets = samples_to_triplets(samples,stats=stats,  bg_mode="zero")
   G = GramianAngularField(image_size=size,method='summation',sample_range=(0, 1))
   S = np.transpose(np.array(sell_triplets))
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
      while True:
         cur = conn.cursor()
         gafInfo = getGafInfo(conn,cur)
         for i in range(len(gafInfo)):
            product = gafInfo[i][0]
            maxSize = gafInfo[i][1]
            midpointSamples = getMidpointSamples(conn,cur,product,maxSize)
            askPriceSamples,askSizeSamples = getAskSamples(conn,cur,product,maxSize)
            bidPriceSamples,bidSizeSamples = getBidSamples(conn,cur,product,maxSize)
            buySamples,sellSamples = getBuyAndSellSamples(conn,cur,product,maxSize)
            shared_stats = fit_shared_stats(buySamples,sellSamples)
            size = len(midpointSamples)
            if size >= 21: 
               with ThreadPoolExecutor(max_workers=4) as executor:
                  future_midpoint = executor.submit(getMidpointFields, midpointSamples, size)
                  future_orderbook = executor.submit(getOrderbookField, askPriceSamples, askSizeSamples, bidPriceSamples, bidSizeSamples, size)
                  future_buy = executor.submit(getBuyField, buySamples, size,shared_stats)
                  future_sell = executor.submit(getSellField, sellSamples, size,shared_stats)
                  midpointFields = future_midpoint.result()
                  orderbookField = future_orderbook.result()
                  buyField = future_buy.result()
                  sellField = future_sell.result()
               midpointImages = getMidpointImages(midpointFields)
               orderbookImage = fieldToRGB(orderbookField)
               buyImage = fieldToRGB(buyField,permutation=[1,0,2])
               sellImage = fieldToRGB(sellField)
               doUpdate(conn,cur,product,size,midpointSamples[0],midpointImages,orderbookImage,buyImage,sellImage)
         conn.commit()
         cur.close()
         currentTime = time.time()
         iterations = iterations + 1
         sleepTime = startTime + iterations*sleepInterval - currentTime
         if sleepTime < 0: sleepTime = 0
         if sleepTime == 0:
            print('calculate: loop has no idle time; engine may be at capacity')
         time.sleep(sleepTime)
   except Exception as e:
      traceback.print_exception(type(e), e, e.__traceback__)
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
