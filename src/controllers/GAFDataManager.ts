
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
      let orderbookImage = g.getOrderbookImage();
      let buyImage = g.getBuyImage();
      let midpoint = g.getMidpoint();
      let midpointImages = g.getMidpointImages();
      let sellImage = g.getSellImage();
      let size = g.getSize();

      return { midpoint:midpoint, png1:orderbookImage, png2:buyImage, png3:sellImage, png4:midpointImages[1], size:size, date:new Date() };
    }
    return { midpoint:null, png1:null, png2:null, png3:null, png4:null, size:0, date:new Date() };
  }
}