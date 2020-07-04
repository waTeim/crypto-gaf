import { Pool, Connection } from './db';

export class GAF
{
  protected static pool:Pool;
  protected static gafs:Map<string,GAF>;

  protected currentData:number[];
  protected maxSize:number;
  protected product:string;
  protected size:number;
  protected updatedData:number[];

  constructor(product:string)
  {
    this.product = product;
  }

  protected async load() {
    let connection = await GAF.pool.getConnection();
    
    let rows = await connection.query(`
      SELECT
        current_data,
        max_size,
        size,
        updated_data
      FROM 
        crypto_gaf.gafs 
      WHERE product = $1
      `,[this.product]);
    if(rows != null && rows.length != 0) {
      this.currentData = rows[0].current_data;
      this.maxSize = rows[0].max_size;
      this.size = rows[0].size;
      this.updatedData = rows[0].updated_data;
    }
    connection.free();
  }

  static async refresh(product:string):Promise<GAF>
  {
    let gaf = GAF.retrieve(product);
    
    if(gaf != null) await gaf.load();
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

  getCurrent():number[]
  {
    return this.currentData;
  }

  getSize()
  {
    return this.size;
  }
}
