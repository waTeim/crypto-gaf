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
  let pgUser = "postgres";
  let pgHost = "pg";
  let pgDb = "postgres";
  let pgPw = "";

  if((pgUrl == null || pgUrl.length == 0) && process.env.PG != null && process.env.PG.length != null) pgUrl = process.env.PG;
  if(process.env.POSTGRES_USER != null && process.env.POSTGRES_USER.length > 0) pgUser = process.env.POSTGRES_USER;
  if(process.env.POSTGRES_HOST != null && process.env.POSTGRES_HOST.length > 0) pgHost = process.env.POSTGRES_HOST;
  if(process.env.POSTGRES_DB != null && process.env.POSTGRES_DB.length > 0) pgDb = process.env.POSTGRES_DB;
  if(process.env.POSTGRES_PW != null && process.env.POSTGRES_PW.length > 0) pgPw = process.env.POSTGRES_PW;
  if(pgUrl == null || pgUrl.length == 0)
  {
    if(pgPw.length > 0) pgUrl = `postgresql://${pgUser}:${pgPw}@${pgHost}/${pgDb}`;
    else pgUrl = `postgresql://${pgUser}@${pgHost}/${pgDb}`;
  }
  try
  {
    if(pgUrl.length > 0) await initServer(pgUrl);
    else program.help();
  }
  catch(e)
  {
    console.log("failed to start: ",e);
  }
}
