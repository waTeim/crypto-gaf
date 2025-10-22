
import { Pool, Connection } from './db';

interface OrderbookEntry
{
  price:number;
  size:number;
  numOrders:number;
};

interface OrderbookInterval
{
  midpoint:number;
  asks:OrderbookEntry[];
  bids:OrderbookEntry[];
};

async function getNext(product:string):Promise<OrderbookInterval>
{
  let asks:OrderbookEntry[] = [];
  let bids:OrderbookEntry[] = [];
  let midpoint:number;

  return { midpoint:midpoint, asks:asks, bids:bids };
}


export async function syncSequences(products:string):Promise<null>
{
  for(let i = 0;i < products.length;i++)
  {
    let price = await getNext(products[i]);

  }
  setTimeout(syncSequences,1000);
  return null;
}