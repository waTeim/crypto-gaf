import argparse
import json
import os
import psycopg2
import psycopg2.extras
import time
import requests

def getOrderbookInfo(product,aggregation,depth):
   res = requests.get('http://coinbase-local:63200/api/orderBook/interval',params={ 'product':product, 'aggregation':aggregation, 'depth':depth })
   if res.status_code == 200:
      parsed = res.json()
      if parsed != None and parsed.get('midpoint',None) != None and parsed.get('asks',None) != None and parsed.get('bids',None) != None:
         midpoint = parsed['midpoint']
         bids = parsed['bids']
         asks = parsed['asks']
         return midpoint,bids,asks
      print("null respond from coinbase-local")
   return None,None,None

def getMarketOrderInfo(product,since):
   res = requests.get('http://coinbase-local:63200/api/orderBook/marketOrders',params={ 'product':product, 'since':since })
   if res.status_code == 200:
      parsed = res.json()
      if parsed != None and parsed.get('sequence',None) != None and parsed.get('buy',None) != None and parsed.get('sell',None) != None:
         sequence = parsed['sequence']
         buy = parsed['buy']
         sell = parsed['sell']
         #print("sequence = {0} buy = {1} sell = {2}".format(sequence,buy,sell))
         return sequence,buy,sell
      print("null respond from coinbase-local")
   return None,None,None

def getGafInfo(conn,cur):
   cur.execute( """
      SELECT product,max_size FROM crypto_gaf.gafs
      """)
   rows = cur.fetchall()
   return [ [x[0],x[1]] for x in rows ]

def doInsert(conn,cur,asks,bids,buy,midpoint,product,sell):
   sql = """
      INSERT INTO crypto_gaf.samples (ask_prices,ask_sizes,bid_prices,bid_sizes,buys,midpoint,product,sells)
      VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
   """
   cur.execute(sql,(
      [ float(x[0]) for x in asks ],
      [ float(x[1]) for x in asks ],
      [ float(x[0]) for x in bids ],
      [ float(x[1]) for x in bids ],
      [ float(buy['price']), float(buy['size']), float(buy['numOrders']) ],
      float(midpoint),
      product,
      [ float(sell['price']), float(sell['size']), float(sell['numOrders']) ]
   ))
   #conn.commit()
   #cur.close()

def doDelete(conn,cur,product,maxSize):
   sql = """
      WITH id_list AS
      ( 
         SELECT sample_id
         FROM crypto_gaf.samples WHERE product = %s 
         ORDER BY sample_id DESC
         LIMIT %s
      ) 
      DELETE FROM crypto_gaf.samples WHERE sample_id NOT IN (SELECT * from id_list)
   """
   cur.execute(sql,(product,maxSize))

def backoff(btime):
   print("backoff {0} seconds".format(btime))
   time.sleep(btime)
   btime = btime*2
   if btime > 60: btime = 60
   return btime

def main(args):
   postgresUser = "postgres"
   postgresPw = None
   postgresHost = "localhost"
   postgresDb = "postgres"
   sleepInterval = 1
   aggregation = 10
   depth = 5
   conn = None
   startTime = None
   iterations = None
   done = False
   btime = 5
   sequences = {}
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
   while not done:
      if startTime == None: startTime = time.time()
      if iterations == None: iterations = 0
      try:
         if conn == None: conn = psycopg2.connect(host=postgresHost,dbname=postgresDb,user=postgresUser,password=postgresPw)
         cur = conn.cursor()
         gafInfo = getGafInfo(conn,cur)
         for i in range(len(gafInfo)):
            product = gafInfo[i][0]
            sequence = sequences.get(product,None)
            midpoint,asks,bids = getOrderbookInfo(product,aggregation,depth)
            sequences[product],buy,sell = getMarketOrderInfo(product,sequence)
            doInsert(conn,cur,asks,bids,buy,midpoint,product,sell)
            doDelete(conn,cur,product,gafInfo[i][1])
         conn.commit()
         cur.close()
         currentTime = time.time()
         iterations = iterations + 1
         sleepTime = startTime + iterations*sleepInterval - currentTime
         if(sleepTime < 0): sleepTime = 0
         btime = 5
         time.sleep(sleepTime)
      except (psycopg2.OperationalError,psycopg2.DatabaseError) as e:
         print(e)
         conn = None
         btime = backoff(btime)
      except requests.RequestException as e:
         print(e)
         conn.rollback()
         btime = backoff(btime)
      except Exception as e:
         print(e)
         done = True

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
