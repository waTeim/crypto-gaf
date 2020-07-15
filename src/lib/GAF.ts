import { Pool, Connection } from './db';

export class GAF
{
  protected static pool:Pool;
  protected static gafs:Map<string,GAF>;

  protected askPriceImages:string[];
  protected bidPriceImages:string[];
  protected maxSize:number;
  protected midpoint:number;
  protected midpointImages:string[];
  protected product:string;
  protected size:number;

  constructor(product:string)
  {
    this.product = product;
  }

  protected async load() {
    let connection = await GAF.pool.getConnection();
    
    let rows = await connection.query(`
      SELECT
        ask_price_images,
        bid_price_images,
        max_size,
        midpoint,
        midpoint_images,
        size
      FROM 
        crypto_gaf.gafs 
      WHERE product = $1
      `,[this.product]);
    if(rows != null && rows.length != 0) {
      this.askPriceImages = rows[0].ask_price_images;
      this.bidPriceImages = rows[0].bid_price_images;
      this.midpoint = rows[0].midpoint;
      this.midpointImages = rows[0].midpoint_images;
      this.maxSize = rows[0].max_size;
      this.size = rows[0].size;
    }
    connection.free();
  }

  static async refresh(product:string):Promise<GAF>
  {
    let gaf = GAF.retrieve(product);
    
    if(gaf != null) await gaf.load();
    else console.log("gaf retrieve = null");
    return gaf;
  }

  static async restore(pool:Pool)
  {
    GAF.pool = pool;
    if(GAF.gafs == null) GAF.gafs = new Map<string,GAF>();

    let connection = await GAF.pool.getConnection();
    let rows = await connection.query(`SELECT product FROM crypto_gaf.gafs`,[]);

    if(rows != null)
    {
      for(let i = 0;i < rows.length;i++)
      {
         let product:string = rows[i].product;
         let gaf = new GAF(product);

         await gaf.load();
         GAF.gafs.set(product,gaf);
      }
    }
    connection.free();
  }

  static retrieve(product:string):GAF
  {
    if(GAF.gafs == null) GAF.gafs = new Map<string,GAF>();
    return GAF.gafs.get(product);
  }

  getAskPriceImages():string[]
  {
    return this.askPriceImages;
  }

  getBidPriceImages():string[]
  {
    return this.bidPriceImages;
  }

  getMidpoint():number
  {
    return this.midpoint;
  }

  getMidpointImages():string[]
  {
    return this.midpointImages;
  }

  getSize()
  {
    return this.size;
  }
}
