
import { ControllerBase, ControllerProperties, get, post, controller, Res } from 'ts-api';
import { GAF } from '../lib/GAF';

const BigNumber = require('bignumber.js');

interface GAFData
{
  date:Date;
  size:number;
  midpoint:number;
  png1:string;
  png2:string;
  png3:string;
  png4:string;
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

  @get('/image') async getGAFImage(product:string):Promise<GAFData>
  {
    let g:GAF = await GAF.refresh(product);

    if(g != null) 
    {
      let askPriceImages = g.getAskPriceImages();
      let bidPriceImages = g.getBidPriceImages();
      let midpoint = g.getMidpoint();
      let midpointImages = g.getMidpointImages();
      let size = g.getSize();

      return { midpoint:midpoint, png1:midpointImages[0], png2:askPriceImages[0], png3:bidPriceImages[0], png4:midpointImages[1], size:size, date:new Date() };
    }
    return { midpoint:null, png1:null, png2:null, png3:null, png4:null, size:0, date:new Date() };
  }
}