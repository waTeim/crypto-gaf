const url = require('url');
import { promisify } from 'util';

const pg = require('pg');

const query = promisify(function(client:any,qs:string,argv:any[],cb:Function) { 
  client.query(qs,argv,function(err:any,res:any) {
    if(err) {
      console.log('pg client query error',err);
      cb(err);
    }
    else {
      if(res.rowCount >= 1) cb(null,res.rows);
      else cb(null,null);
    }
  });
});

const getConnectionFromPool = promisify(function(pool:any,cb:Function) {
  pool.connect(function(err:any,client:any,free:Function) {
    if(err) return cb(`pg_connection error: ${err}`);
    cb(null,new Connection(client,free));
  });
});

export class Connection {
  protected client:any;

  constructor(client:any,free:Function) {
    this.client = client;
    this.free = free;
  }

  free:Function;

  async query(qs:string,argv:any[]):Promise<any[]> {
     let res = await query(this.client,qs,argv);
     return <any[]>res;
  }
}

export class Pool {
  protected pool:any;

  constructor(connectInfo:string) {
    let params = url.parse(connectInfo);
    let auth;
    let user;
    let password;

    if(params.auth != null) {
      auth = params.auth.split(':');
      user = auth[0];
      password = auth[1];
    }

    let config = {
      user: user,
      password: password,
      host: params.hostname,
      port: params.port,
      database: connectInfo.split('/')[3]
    };

    this.pool = new pg.Pool(config);
  }

  async getConnection():Promise<Connection> {
    let connection:unknown = getConnectionFromPool(this.pool);

    return <Connection>connection;
  }
}