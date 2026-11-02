#!/usr/bin/env node
'use strict';
// Minimal same-origin Node.js backend. No third-party dependencies.
const http=require('node:http');
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const ROOT=__dirname;
const PUBLIC=path.join(ROOT,'public');
const DATA=process.env.DATA_DIR||path.join(ROOT,'private-data');
const USERS_FILE=path.join(DATA,'اطلاعات کاربران.txt');
const RESULTS_FILE=path.join(DATA,'نتایج بازی کاربران.txt');
const SESSIONS_FILE=path.join(DATA,'sessions.json');
const PORT=Number(process.env.PORT||3000);
const MAX_BODY=32*1024;
const RETENTION_MS=24*30*86400*1000;
const CONSENT_VERSION='2026-11-01-v1';
const rate=new Map();
function ensureData(){fs.mkdirSync(DATA,{recursive:true,mode:0o700});try{fs.chmodSync(DATA,0o700)}catch(_){}for(const f of [USERS_FILE,RESULTS_FILE]){if(!fs.existsSync(f))fs.writeFileSync(f,'',{mode:0o600});try{fs.chmodSync(f,0o600)}catch(_){}}}
function getKey(){const raw=process.env.DATA_ENCRYPTION_KEY||'';if(!/^[a-f0-9]{64}$/i.test(raw))throw new Error('DATA_ENCRYPTION_KEY must be a 32-byte hex string.');return Buffer.from(raw,'hex')}
let KEY;
function encryptRecord(value){const iv=crypto.randomBytes(12),cipher=crypto.createCipheriv('aes-256-gcm',KEY,iv);const body=Buffer.concat([cipher.update(JSON.stringify(value),'utf8'),cipher.final()]);const tag=cipher.getAuthTag();return `enc:v1:${iv.toString('base64')}:${tag.toString('base64')}:${body.toString('base64')}`;}
// Use a compact, delimiter-safe encrypted record format.
function decryptLine(line){const m=line.trim().match(/^enc:v1:([^:]+):([^:]+):([^:]+)$/);if(!m)throw new Error('Encrypted record format is invalid.');try{const iv=Buffer.from(m[1],'base64'),tag=Buffer.from(m[2],'base64'),ct=Buffer.from(m[3],'base64');const d=crypto.createDecipheriv('aes-256-gcm',KEY,iv);d.setAuthTag(tag);return JSON.parse(Buffer.concat([d.update(ct),d.final()]).toString('utf8'));}catch(_){throw new Error('Unable to decrypt encrypted record; check DATA_ENCRYPTION_KEY and data integrity.');}}
function appendEncrypted(file,obj){fs.appendFileSync(file,encryptRecord(obj)+'\n',{encoding:'utf8',mode:0o600});try{fs.chmodSync(file,0o600)}catch(_){}}
function readSessions(){try{const x=JSON.parse(fs.readFileSync(SESSIONS_FILE,'utf8'));return x&&typeof x==='object'?x:{}}catch(_){return {}}}
let sessions={};
function saveSessions(){const tmp=SESSIONS_FILE+'.tmp';fs.writeFileSync(tmp,JSON.stringify(sessions,null,2),{mode:0o600});fs.renameSync(tmp,SESSIONS_FILE);try{fs.chmodSync(SESSIONS_FILE,0o600)}catch(_){}}
function rewriteEncrypted(file,keep){const lines=fs.existsSync(file)?fs.readFileSync(file,'utf8').split(/\r?\n/).filter(Boolean):[];const next=[];for(const line of lines){const v=decryptLine(line);if(!v)throw new Error('Encrypted record is invalid; refusing to rewrite data.');if(keep(v))next.push(line)}const tmp=file+'.tmp';fs.writeFileSync(tmp,next.length?next.join('\n')+'\n':'',{mode:0o600});fs.renameSync(tmp,file);try{fs.chmodSync(file,0o600)}catch(_){}}
function purgeExpired(){const now=Date.now(),expired=new Set();for(const [key,s] of Object.entries(sessions)){if(!s||now-Number(s.lastActivity||s.createdAt||0)>RETENTION_MS)expired.add(s.userId);}
 const activeIds=new Set(Object.values(sessions).map(s=>s.userId));
 rewriteEncrypted(USERS_FILE,r=>activeIds.has(r.userId)&&!expired.has(r.userId));
 rewriteEncrypted(RESULTS_FILE,r=>activeIds.has(r.userId)&&!expired.has(r.userId)&&Date.now()-new Date(r.completedAt||0).getTime()<=RETENTION_MS);
 if(expired.size){for(const [k,s] of Object.entries(sessions))if(expired.has(s.userId))delete sessions[k];saveSessions();}}
function json(res,status,obj){res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'});res.end(JSON.stringify(obj));}
function rateLimit(req,res){const ip=(req.socket.remoteAddress||'unknown').replace(/^::ffff:/,'');const now=Date.now(),a=(rate.get(ip)||[]).filter(t=>now-t<60000);if(a.length>=40){json(res,429,{ok:false,message:'درخواست‌های زیادی ارسال شده است.'});return false}a.push(now);rate.set(ip,a);return true;}
function readBody(req){return new Promise((resolve,reject)=>{let n=0,chunks=[];req.on('data',c=>{n+=c.length;if(n>MAX_BODY){reject(new Error('BODY_TOO_LARGE'));req.destroy();return}chunks.push(c)});req.on('end',()=>{try{resolve(JSON.parse(Buffer.concat(chunks).toString('utf8')||'{}'))}catch(_){reject(new Error('INVALID_JSON'))}});req.on('error',reject)});}
function jalaliMatches(iso,jalali){try{const d=new Date(iso+'T12:00:00Z');const parts={};for(const p of new Intl.DateTimeFormat('en-US-u-ca-persian',{year:'numeric',month:'numeric',day:'numeric',timeZone:'UTC'}).formatToParts(d))if(['year','month','day'].includes(p.type))parts[p.type]=Number(p.value);const digits=String(jalali||'').replace(/[۰-۹]/g,d=>'۰۱۲۳۴۵۶۷۸۹'.indexOf(d)).replace(/[٠-٩]/g,d=>'٠١٢٣٤٥٦٧٨٩'.indexOf(d));const m=digits.match(/^(\d{4})[\/.-](\d{1,2})[\/.-](\d{1,2})$/);return !!m&&Number(m[1])===parts.year&&Number(m[2])===parts.month&&Number(m[3])===parts.day}catch(_){return false}}
function validProfile(p){if(!p||typeof p!=='object')return false;const str=(v,max)=>typeof v==='string'&&v.trim().length>0&&v.length<=max;return str(p.firstName,60)&&str(p.lastName,80)&&['زن','مرد','غیردودویی/سایر','ترجیح می‌دهم اعلام نکنم'].includes(p.gender)&&/^\+[1-9]\d{6,14}$/.test(p.phone||'')&&/^\d{4}-\d{2}-\d{2}$/.test(p.birthDateISO||'')&&str(p.birthDateJalali,20)&&str(p.education,60)&&str(p.occupation,100)&&typeof p.researchConsent==='boolean'&&p.consentVersion===CONSENT_VERSION;}
function findAuth(req){const token=(req.headers.authorization||'').replace(/^Bearer\s+/i,'');if(!token||token.length<30)return null;const hash=crypto.createHash('sha256').update(token).digest('hex');for(const [clientId,s] of Object.entries(sessions))if(s.tokenHash===hash)return {clientId,session:s};return null;}
function originAllowed(req){const origin=req.headers.origin;if(!origin)return true;try{return new URL(origin).host===String(req.headers.host||'')}catch(_){return false}}
async function handle(req,res){
 res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('Referrer-Policy','no-referrer');res.setHeader('X-Frame-Options','DENY');res.setHeader('Permissions-Policy','camera=(), microphone=(), geolocation=()');
 if(!originAllowed(req))return json(res,403,{ok:false,message:'مبدأ درخواست مجاز نیست.'});
 const url=new URL(req.url,'http://localhost');
 if(req.method==='GET'&&url.pathname==='/api/health')return json(res,200,{ok:true,service:'shahr-e-ayeneh-api',storage:'encrypted-text'});
 if(req.method==='GET'&&(url.pathname==='/'||url.pathname==='/index.html')){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-cache'});return fs.createReadStream(path.join(PUBLIC,'index.html')).pipe(res)}
 if(req.method==='GET'&&url.pathname==='/favicon.ico'){res.writeHead(204);return res.end()}
 if(!url.pathname.startsWith('/api/'))return json(res,404,{ok:false,message:'یافت نشد.'});
 if(!rateLimit(req,res))return;
 let body={};if(req.method==='POST'||req.method==='PUT'){try{body=await readBody(req)}catch(e){return json(res,e.message==='BODY_TOO_LARGE'?413:400,{ok:false,message:'درخواست معتبر نیست.'})}}
 if(req.method==='POST'&&url.pathname==='/api/register'){
  const p=body.profile,clientId=body.clientProfileId;
  if(typeof clientId!=='string'||! /^[a-zA-Z0-9-]{20,80}$/.test(clientId)||!validProfile(p))return json(res,400,{ok:false,message:'اطلاعات پروفایل معتبر نیست.'});
  const dob=new Date(p.birthDateISO+'T12:00:00Z');if(!Number.isFinite(dob.getTime())||dob.toISOString().slice(0,10)!==p.birthDateISO||p.birthDateISO>new Date().toISOString().slice(0,10)||!jalaliMatches(p.birthDateISO,p.birthDateJalali))return json(res,400,{ok:false,message:'تاریخ تولد شمسی و میلادی با هم مطابقت ندارند.'});
  let age=new Date().getUTCFullYear()-dob.getUTCFullYear();const now=new Date();if(now.getUTCMonth()<dob.getUTCMonth()||(now.getUTCMonth()===dob.getUTCMonth()&&now.getUTCDate()<dob.getUTCDate()))age--;
  if(age<0||age>120)return json(res,400,{ok:false,message:'سن یا تاریخ تولد معتبر نیست.'});
  if(p.researchConsent&&age<18)return json(res,400,{ok:false,message:'برای افراد زیر ۱۸ سال، رضایت سرپرست و فرایند پژوهشی جداگانه لازم است.'});
  const old=sessions[clientId],userId=old?.userId||crypto.randomUUID(),token=crypto.randomBytes(32).toString('base64url');
  const profileRecord={recordType:'user-profile',userId,profile:{firstName:p.firstName.trim(),lastName:p.lastName.trim(),gender:p.gender,phone:p.phone,birthDateJalali:p.birthDateJalali,birthDateISO:p.birthDateISO,education:p.education,occupation:p.occupation.normalize('NFC').trim()},researchConsent:!!p.researchConsent,consentVersion:CONSENT_VERSION,recordedAt:new Date().toISOString()};
  rewriteEncrypted(USERS_FILE,r=>r.userId!==userId);
  appendEncrypted(USERS_FILE,profileRecord);
  sessions[clientId]={userId,tokenHash:crypto.createHash('sha256').update(token).digest('hex'),researchConsent:!!p.researchConsent,consentVersion:CONSENT_VERSION,createdAt:old?.createdAt||Date.now(),lastActivity:Date.now()};saveSessions();
  if(!p.researchConsent)rewriteEncrypted(RESULTS_FILE,r=>r.userId!==userId);
  return json(res,200,{ok:true,userId,token,createdAt:new Date().toISOString(),researchConsent:!!p.researchConsent});
 }
 if(req.method==='POST'&&url.pathname==='/api/activity'){
  const auth=findAuth(req);if(!auth)return json(res,401,{ok:false,message:'نشست معتبر نیست.'});auth.session.lastActivity=Date.now();saveSessions();return json(res,200,{ok:true});
 }
 if(req.method==='POST'&&url.pathname==='/api/results'){
  const auth=findAuth(req);if(!auth)return json(res,401,{ok:false,message:'نشست معتبر نیست.'});if(!auth.session.researchConsent)return json(res,403,{ok:false,message:'رضایت پژوهشی فعال نیست.'});
  const p=body;if(!Number.isInteger(p.stageId)||p.stageId<1||p.stageId>389||typeof p.correct!=='boolean'||!Number.isFinite(Number(p.score)))return json(res,400,{ok:false,message:'نتیجهٔ مرحله معتبر نیست.'});
  const safe={recordType:'stage-result',userId:auth.session.userId,consentVersion:auth.session.consentVersion,stageId:p.stageId,city:String(p.city||'').slice(0,100),caseType:String(p.caseType||'case').slice(0,40),patternIds:Array.isArray(p.patternIds)?p.patternIds.filter(x=>typeof x==='string').slice(0,4):[],conflictIds:Array.isArray(p.conflictIds)?p.conflictIds.filter(x=>typeof x==='string'||Number.isInteger(x)).slice(0,4):[],correct:p.correct,score:Math.max(0,Math.min(1000000,Math.floor(Number(p.score)))),completedAt:new Date().toISOString()};
  appendEncrypted(RESULTS_FILE,safe);auth.session.lastActivity=Date.now();saveSessions();return json(res,201,{ok:true,saved:true});
 }
 if(req.method==='DELETE'&&url.pathname==='/api/account'){
  const auth=findAuth(req);if(!auth)return json(res,401,{ok:false,message:'نشست معتبر نیست.'});const uid=auth.session.userId;
  rewriteEncrypted(USERS_FILE,r=>r.userId!==uid);rewriteEncrypted(RESULTS_FILE,r=>r.userId!==uid);for(const [k,s] of Object.entries(sessions))if(s.userId===uid)delete sessions[k];saveSessions();return json(res,200,{ok:true,deleted:true});
 }
 return json(res,404,{ok:false,message:'مسیر API پیدا نشد.'});
}
try{ensureData();KEY=getKey();sessions=readSessions();purgeExpired();}catch(e){console.error('Server startup blocked:',e.message);process.exit(1)}
const server=http.createServer((req,res)=>{handle(req,res).catch(e=>{console.error('Request error:',e.message);if(!res.headersSent)json(res,500,{ok:false,message:'خطای داخلی سرور.'});else res.destroy()})});
server.listen(PORT,'0.0.0.0',()=>console.log(`Shahr-e-Ayeneh server listening on ${PORT}`));
