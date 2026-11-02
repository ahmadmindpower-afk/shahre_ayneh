#!/usr/bin/env node
'use strict';
// Admin-only export. Run only on a trusted machine with DATA_ENCRYPTION_KEY set.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const DATA=process.env.DATA_DIR||path.join(__dirname,'private-data');
const KEY=Buffer.from(process.env.DATA_ENCRYPTION_KEY||'','hex');
if(KEY.length!==32){console.error('DATA_ENCRYPTION_KEY must be a 32-byte hex string.');process.exit(1)}
function decrypt(line){const m=line.match(/^enc:v1:([^:]+):([^:]+):([^:]+)$/);if(!m)return null;const d=crypto.createDecipheriv('aes-256-gcm',KEY,Buffer.from(m[1],'base64'));d.setAuthTag(Buffer.from(m[2],'base64'));return JSON.parse(Buffer.concat([d.update(Buffer.from(m[3],'base64')),d.final()]).toString('utf8'))}
function read(name){const f=path.join(DATA,name);if(!fs.existsSync(f))return[];return fs.readFileSync(f,'utf8').split(/\r?\n/).filter(Boolean).map(x=>{try{return decrypt(x)}catch(_){return null}}).filter(Boolean)}
const mode=process.argv[2];const users=read('اطلاعات کاربران.txt'),results=read('نتایج بازی کاربران.txt');const out=path.join(DATA,'exports');fs.mkdirSync(out,{recursive:true,mode:0o700});try{fs.chmodSync(out,0o700)}catch(_){}
if(mode==='profiles'){
 const txt=users.filter(x=>x.recordType==='user-profile').map(x=>JSON.stringify(x)).join('\n')+'\n';const f=path.join(out,'اطلاعات کاربران-خروجی مدیر.txt');fs.writeFileSync(f,txt,{mode:0o600});try{fs.chmodSync(f,0o600)}catch(_){}console.log(`Wrote ${users.length} encrypted profile records to ${f}`);
}else if(mode==='research'){
 const rows=results.filter(x=>x.recordType==='stage-result');const city={},stage={},correct={correct:0,incorrect:0};for(const r of rows){city[r.city]=(city[r.city]||0)+1;stage[r.stageId]=(stage[r.stageId]||0)+1;correct[r.correct?'correct':'incorrect']++}
 const latest=new Map();for(const u of users)if(u.recordType==='user-profile'&&u.researchConsent)latest.set(u.userId,u.profile);
 const byGender={},byEducation={},byOccupation={},byAgeBand={};for(const uid of new Set(rows.map(x=>x.userId))){const p=latest.get(uid);if(!p)continue;byGender[p.gender]=(byGender[p.gender]||0)+1;byEducation[p.education]=(byEducation[p.education]||0)+1;byOccupation[p.occupation]=(byOccupation[p.occupation]||0)+1;const born=new Date((p.birthDateISO||'')+'T12:00:00Z');const now=new Date();let age=Number.isFinite(born.getTime())?now.getUTCFullYear()-born.getUTCFullYear():-1;if(age>=0&&(now.getUTCMonth()<born.getUTCMonth()||(now.getUTCMonth()===born.getUTCMonth()&&now.getUTCDate()<born.getUTCDate())))age--;if(age>=0){const band=age<25?'18-24':age<35?'25-34':age<45?'35-44':age<55?'45-54':'55+';byAgeBand[band]=(byAgeBand[band]||0)+1}}
 const report={generatedAt:new Date().toISOString(),totalStageResults:rows.length,uniquePseudonymousParticipants:new Set(rows.map(x=>x.userId)).size,correct,byCity:city,byStage:stage,demographics:{byGender,byEducation,byOccupation,byAgeBand},notice:'Aggregated research summary; no direct identifiers or pseudonymous user IDs are included.'};
 const f=path.join(out,'گزارش پژوهشی-تجمیعی.json');fs.writeFileSync(f,JSON.stringify(report,null,2),{mode:0o600});try{fs.chmodSync(f,0o600)}catch(_){}console.log(`Wrote aggregated research report to ${f}`);
}else{console.log('Usage: node export-data.js profiles | research')}
