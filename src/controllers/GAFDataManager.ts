
import { ControllerBase, ControllerProperties, get, post, controller, Res } from 'ts-api';
import { GAF } from '../lib/GAF';

const BigNumber = require('bignumber.js');

interface GAFData
{
  date:Date;
  data:number[][];
};

/**
 * Query the orderbook
 */
@controller('/gaf')
export default class GAFManager extends ControllerBase
{
  protected static source:GAF;

  constructor(properties:ControllerProperties)
  {
    super(properties);
  }

  @get('/current') async getGAF(product:string):Promise<GAFData>
  {
    let g:GAF = await GAF.refresh(product);
    let data:GAFData;

    if(g != null) 
    {
      let current = g.getCurrent();
      let size = g.getSize();

      data.date = new Date();
      for(let i = 0;i < size;i++)
      {
        data.data.push([]);
        for(let j = 0;j < size;j++) data.data[i].push(current[i*size + j]);
      }
      return data;
    }
    return { data:null, date:new Date() };
  }
}