import init from './init';

let PORT:number;

if(process.env.PORT != null) PORT = parseInt(process.env.PORT);
else PORT = 63500;

async function initServer(pgUrl:string)
{
  let app:any = await init(pgUrl);
  let server = app.listen(PORT, () => { console.log(`App is running at http://localhost:${PORT}`); });

  return server;
}

export default async function main(program:any)
{
  let pgUrl:string = program.args[0];

  if(pgUrl.length == 0 && process.env.PG != null && process.env.PG.length != 0) pgUrl = process.env.PG;
  if(pgUrl.length > 0) await initServer(pgUrl);
  else program.help();
}
