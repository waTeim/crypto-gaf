const cors = require('cors');

import express from 'express';
import * as bodyParser from 'body-parser';
import { Router } from './Router';
import { Pool } from '../lib/db';
import { GAF } from '../lib/GAF';

const app = express();

async function initRouter(app: express.Application,context:any)
{
  const router  = new Router(context);

  app.use(cors());
  app.use((req, _res, next) => {
    console.log(`[spa] ${req.method} ${req.originalUrl}`);
    next();
  });
  app.use(bodyParser.urlencoded({ extended:false }));
  app.use(bodyParser.json());
  app.use(router.getExpressRouter());
  app.use((req, res) => {
    console.warn(`[spa] 404 ${req.originalUrl}`);
    res.status(404).json({ error: 'Not Found' });
  });
  app.use((err: Error, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
    console.error('[spa] handler error:', err);
    res.status(500).json({ error: 'Internal Server Error' });
  });
}

export default async function init(pgUrl:string)
{
  try
  {
    let pool:Pool = new Pool(pgUrl);

    await initRouter(app,{});
    await GAF.restore(pool);
    return app;
  }
  catch(e)
  {
    console.error('Error in initAppStartup:',e);
    throw new Error(e);
  }
}
