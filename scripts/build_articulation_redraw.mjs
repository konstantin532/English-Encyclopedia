// Original schematic geometry; no traced or external artwork.
// Generate SVGs with: node scripts/build_articulation_redraw.mjs
// Add deterministic, non-browser PNG previews with --preview. These do NOT replace Playwright QA.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const state = {
  "art": {
    "viewBox": [
      0,
      0,
      520,
      500
    ],
    "palette": {
      "paper": "#fffdf9",
      "skin": "#f0e5dc",
      "ink": "#4c585c",
      "soft": "#dfc5ba",
      "cavity": "#fffaf4",
      "tongue": "#c77f7d",
      "tongueLine": "#945d61",
      "air": "#397b92",
      "voice": "#80658a",
      "tooth": "#ffffff"
    },
    "fixed": [
      {
        "part": "skin",
        "d": "M160 470 L157 383 C126 355 106 321 99 280 C85 225 90 164 118 126 C146 85 193 67 240 70 C295 73 335 101 353 148 C360 166 359 185 367 197 C373 205 366 214 365 221 C372 239 389 250 410 262 C423 271 421 280 407 284 C402 286 398 287 396 291 L393 305 L386 368 C393 379 391 390 380 399 C361 415 333 421 310 427 C286 433 266 430 247 422 L240 470 Z",
        "fill": "skin",
        "stroke": null
      },
      {
        "part": "profile",
        "d": "M160 470 L157 383 C126 355 106 321 99 280 C85 225 90 164 118 126 C146 85 193 67 240 70 C295 73 335 101 353 148 C360 166 359 185 367 197 C373 205 366 214 365 221 C372 239 389 250 410 262 C423 271 421 280 407 284 C402 286 398 287 396 291 L393 305 M386 368 C393 379 391 390 380 399 C361 415 333 421 310 427 C286 433 266 430 247 422 L240 470",
        "fill": null,
        "stroke": "ink",
        "width": 2.2
      },
      {
        "part": "brow",
        "d": "M329 208 Q342 201 354 211",
        "fill": null,
        "stroke": "ink",
        "width": 2.2
      },
      {
        "part": "eye",
        "d": "M332 220 Q342 215 351 222 Q341 227 332 220 M347 219 L347 223",
        "fill": null,
        "stroke": "ink",
        "width": 1.8
      },
      {
        "part": "nostril",
        "d": "M395 279 Q399 273 407 278",
        "fill": null,
        "stroke": "ink",
        "width": 1.5
      },
      {
        "part": "ear-orientation",
        "d": "M164 224 C149 213 134 224 134 243 C133 263 143 280 154 277 C164 275 169 255 165 242 M157 232 Q143 229 145 247 Q157 241 158 253 Q148 256 153 266",
        "fill": null,
        "stroke": "soft",
        "width": 2
      },
      {
        "part": "nasal-cavity",
        "d": "M395 287 C379 282 372 264 367 247 C358 231 335 222 311 226 C278 231 252 249 235 271 C261 276 282 280 306 281 C336 283 364 282 388 292 Z",
        "fill": "cavity",
        "stroke": "soft",
        "width": 1.8
      },
      {
        "part": "nasal-cavity-inner",
        "d": "M368 255 Q333 239 305 250 M365 269 Q330 255 299 266",
        "fill": null,
        "stroke": "soft",
        "width": 1.2
      },
      {
        "part": "oral-cavity",
        "d": "M232 273 C218 306 216 350 223 387 L222 438 L244 438 L247 410 C285 405 327 390 357 371 C373 362 383 350 386 337 L385 303 C371 291 358 290 346 288 C318 280 289 280 269 287 L249 289 Z",
        "fill": "cavity",
        "stroke": null
      },
      {
        "part": "pharynx",
        "d": "M232 273 C218 306 216 350 223 387 L222 438 M244 438 L247 410",
        "fill": null,
        "stroke": "ink",
        "width": 1.9
      },
      {
        "part": "hard-palate",
        "d": "M269 287 C292 280 319 282 344 288 C358 291 365 294 368 302 C372 301 375 303 377 307",
        "fill": null,
        "stroke": "ink",
        "width": 2
      },
      {
        "part": "mouth-floor",
        "d": "M371 356 C348 380 304 399 267 403",
        "fill": null,
        "stroke": "soft",
        "width": 1.6
      },
      {
        "part": "upper-teeth",
        "d": "M376 305 L387 305 L388 325 Q382 329 378 325 Z",
        "fill": "tooth",
        "stroke": "ink",
        "width": 1.7
      },
      {
        "part": "larynx",
        "d": "M222 414 Q233 410 244 414 L244 430 Q233 434 222 430 Z",
        "fill": "soft",
        "stroke": "ink",
        "width": 1.4
      }
    ],
    "oralVelum": {
      "part": "velum",
      "d": "M269 287 C255 286 248 269 233 269 L231 279 C247 283 248 297 266 295",
      "fill": "soft",
      "stroke": "ink",
      "width": 1.6
    },
    "lowerTooth": {
      "part": "lower-teeth",
      "d": "M376 343 Q382 340 387 344 L385 358 L375 358 Z",
      "fill": "tooth",
      "stroke": "ink",
      "width": 1.7
    },
    "tongues": {
      "v": "M250 401 C244 381 246 358 264 346 C285 332 307 336 328 342 C343 346 357 350 367 350 Q372 351 369 357 C348 377 313 393 277 408 Z",
      "th": "M250 401 C242 378 246 350 264 337 C283 323 307 329 328 333 C351 337 374 337 389 333 Q400 329 405 333 Q407 336 400 339 C390 342 382 342 376 345 C354 369 308 397 277 408 Z",
      "sz": "M250 401 C244 379 249 351 269 338 C287 326 315 331 337 323 Q350 317 359 312 Q366 311 366 317 C364 331 366 345 364 353 C343 375 308 396 277 408 Z",
      "w": "M250 401 C242 377 244 340 258 318 C267 303 279 301 291 313 C308 330 317 341 339 347 Q355 352 368 351 Q372 353 368 358 C348 379 311 397 277 408 Z"
    },
    "lips": {
      "v": [
        {
          "part": "upper-lip",
          "d": "M393 305 C398 304 403 307 405 311 Q402 315 393 315 L387 312 L387 305 Z",
          "fill": "tongue",
          "stroke": "tongueLine",
          "width": 1.5
        },
        {
          "part": "lower-lip",
          "d": "M379 326 C385 324 390 326 396 331 C403 334 404 339 400 345 C396 350 389 352 386 360 L386 368 Q381 362 379 355 C382 347 386 339 384 333 Z",
          "fill": "tongue",
          "stroke": "tongueLine",
          "width": 1.5
        }
      ],
      "th": [
        {
          "part": "upper-lip",
          "d": "M393 305 C400 306 406 309 408 313 Q410 317 404 319 L389 319 L387 305 Z",
          "fill": "tongue",
          "stroke": "tongueLine",
          "width": 1.5
        },
        {
          "part": "lower-lip",
          "d": "M390 343 Q399 340 407 344 Q413 348 405 353 C395 357 390 362 386 368 L382 357 Q385 350 390 343 Z",
          "fill": "tongue",
          "stroke": "tongueLine",
          "width": 1.5
        }
      ],
      "sz": [
        {
          "part": "upper-lip",
          "d": "M393 305 C400 306 406 309 408 313 Q410 317 404 319 L389 319 L387 305 Z",
          "fill": "tongue",
          "stroke": "tongueLine",
          "width": 1.5
        },
        {
          "part": "lower-lip",
          "d": "M390 332 Q400 330 408 334 Q413 338 406 343 C396 349 390 358 386 368 L382 350 Q385 340 390 332 Z",
          "fill": "tongue",
          "stroke": "tongueLine",
          "width": 1.5
        }
      ],
      "w": [
        {
          "part": "upper-lip",
          "d": "M393 305 C401 304 412 304 418 308 Q426 313 427 319 L414 323 C406 319 399 317 390 316 L387 305 Z",
          "fill": "tongue",
          "stroke": "tongueLine",
          "width": 1.5
        },
        {
          "part": "lower-lip",
          "d": "M390 340 C402 343 415 341 426 334 Q428 343 420 349 C411 357 397 354 391 360 L386 368 L382 357 Q385 346 390 340 Z",
          "fill": "tongue",
          "stroke": "tongueLine",
          "width": 1.5
        }
      ]
    },
    "airs": {
      "v": "M233 409 C230 388 235 357 252 336 C276 309 315 314 348 320 L365 322 M411 322 L438 322",
      "th": "M233 409 C232 382 232 355 253 333 C282 309 315 318 346 323 Q370 328 394 329 L441 329",
      "sz": "M233 409 C234 379 239 351 257 331 C285 308 327 304 355 307 Q368 308 373 319 Q377 330 394 330 L441 330",
      "w": "M233 409 C232 376 236 334 254 309 C265 294 281 293 296 310 C319 339 354 330 388 330 L451 330"
    }
  },
  "fronts": {
    "front-w": [
      {
        "part": "lips",
        "d": "M50 18 C29 18 18 33 18 57 C18 81 30 96 50 96 C70 96 82 81 82 57 C82 33 71 18 50 18 Z",
        "fill": "tongue",
        "stroke": "tongueLine",
        "width": 1.5
      },
      {
        "part": "opening",
        "d": "M50 35 C39 35 34 43 34 57 C34 71 39 79 50 79 C61 79 66 71 66 57 C66 43 61 35 50 35 Z",
        "fill": "cavity",
        "stroke": "tongueLine",
        "width": 1.3
      },
      {
        "part": "airflow",
        "d": "M50 102 L50 119 M45 113 L50 119 L55 113",
        "stroke": "air",
        "width": 2
      }
    ],
    "front-v": [
      {
        "part": "upper-lip",
        "d": "M8 51 C21 40 30 26 43 31 Q50 37 57 31 C70 26 79 40 92 51 Q73 44 50 44 Q27 44 8 51 Z",
        "fill": "tongue",
        "stroke": "tongueLine",
        "width": 1.5
      },
      {
        "part": "lower-lip",
        "d": "M8 56 C23 58 36 59 50 59 C64 59 77 58 92 56 C80 74 64 83 50 83 C36 83 20 74 8 56 Z",
        "fill": "tongue",
        "stroke": "tongueLine",
        "width": 1.5
      },
      {
        "part": "upper-teeth",
        "d": "M31 43 L69 43 L69 59 L31 59 Z M50 43 L50 59",
        "fill": "tooth",
        "stroke": "ink",
        "width": 1.5
      },
      {
        "part": "airflow",
        "d": "M50 96 L50 113 M45 107 L50 113 L55 107",
        "stroke": "air",
        "width": 2
      }
    ]
  },
  "meta": {
    "base": [
      "Общая основа: голова сбоку в разрезе",
      "Голова смотрит вправо. Видны глаз, нос, губы, передние зубы, нёбо, носовая полость, язык и голосовые складки. Показано положение для V."
    ],
    "theta-s": [
      "Вместо TH часто получается «с»",
      "Голова сбоку. Для «с» зубы почти сомкнуты, кончик языка за зубами, воздух идёт узкой струёй. Голоса нет."
    ],
    "theta": [
      "TH: правильное положение языка",
      "Голова сбоку. Расслабленный кончик языка виден между зубами. Воздух непрерывно проходит над кончиком языка. Голоса нет."
    ],
    "eth-z": [
      "Вместо TH часто получается «з»",
      "Голова сбоку. Для «з» зубы почти сомкнуты, кончик языка за зубами, воздух идёт узкой струёй. Голос есть."
    ],
    "eth": [
      "TH с голосом: правильное положение языка",
      "Голова сбоку. Расслабленный кончик языка виден между зубами. Воздух непрерывно проходит над кончиком языка. Голос есть."
    ],
    "w-v": [
      "Вместо W часто получается «в»",
      "Голова сбоку. Верхние передние зубы касаются внутренней стороны нижней губы. Губы не собраны трубочкой. Голос есть."
    ],
    "w": [
      "W: губы трубочкой",
      "Голова сбоку. Губы округлены и выдвинуты вперёд; зубы губ не касаются. Задняя часть языка поднята к мягкому нёбу. Голос есть."
    ],
    "v": [
      "V: правильное положение губ и зубов",
      "Голова сбоку. Верхние передние зубы мягко касаются внутренней стороны нижней губы, язык расслаблен. Голос есть."
    ],
    "front-w": [
      "W: губы спереди",
      "Губы округлены трубочкой. В центре открытое отверстие. Зубы губ не касаются."
    ],
    "front-v": [
      "V: губы спереди",
      "Верхние передние зубы мягко лежат на внутренней стороне нижней губы."
    ]
  },
  "font": {
    "З": "M0 0 L3 0 Q4 0 4 1.5 Q4 3 2 3 Q4 3 4 4.5 Q4 6 3 6 L0 6",
    "У": "M0 0 L2 3 L4 0 M2 3 L0 6",
    "Б": "M4 0 L0 0 L0 6 L2.5 6 Q4 6 4 4.5 Q4 3 2.5 3 L0 3",
    "Ы": "M0 0 L0 6 L1.5 6 Q3 6 3 4.5 Q3 3 1.5 3 L0 3 M4.5 0 L4.5 6",
    "Г": "M0 6 L0 0 L4 0",
    "Я": "M4 6 L4 0 L1.5 0 Q0 0 0 1.5 Q0 3 1.5 3 L4 3 M2 3 L0 6",
    "К": "M0 0 L0 6 M4 0 L0 3 L4 6",
    "О": "M2 0 C0 0 0 1 0 3 C0 5 0 6 2 6 C4 6 4 5 4 3 C4 1 4 0 2 0 Z",
    "Л": "M0 6 L1.5 0 L4 0 L4 6",
    "С": "M4 0 L2 0 C0 0 0 1 0 3 C0 5 0 6 2 6 L4 6",
    "Е": "M4 0 L0 0 L0 6 L4 6 M0 3 L3 3",
    "Т": "M0 0 L4 0 M2 0 L2 6",
    "Ь": "M0 0 L0 6 L2.5 6 Q4 6 4 4.5 Q4 3 2.5 3 L0 3",
    "Н": "M0 0 L0 6 M4 0 L4 6 M0 3 L4 3",
    "В": "M0 6 L0 0 L2.5 0 Q4 0 4 1.5 Q4 3 2.5 3 L0 3 M2.5 3 Q4 3 4 4.5 Q4 6 2.5 6 Z",
    "П": "M0 6 L0 0 L4 0 L4 6",
    "Р": "M0 6 L0 0 L2.5 0 Q4 0 4 1.5 Q4 3 2.5 3 L0 3",
    "И": "M0 0 L0 6 L4 0 L4 6",
    "Д": "M0 6 L1 0 L4 0 L4 6 M0 5.5 L5 5.5 L5 7 M0 5.5 L0 7",
    "А": "M0 6 L2 0 L4 6 M1 3.5 L3 3.5",
    "Х": "M0 0 L4 6 M4 0 L0 6",
    "М": "M0 6 L0 0 L2 3 L4 0 L4 6",
    " ": null
  }
};
function load(key) { return state[key]; }
function geometry(name="v"){
 const a=load("art"), kind=name.startsWith("theta")||name.startsWith("eth")?(name.endsWith("-s")||name.endsWith("-z")?"sz":"th"):name==="w"?"w":"v";
 const voiced=!name.startsWith("theta");
 const shapes=[...a.fixed,a.oralVelum];
 const tooth={...a.lowerTooth};
 if(kind==="sz") tooth.transform=[1,1,0,-10];
 shapes.push({part:"tongue",d:a.tongues[kind],fill:"tongue",stroke:"tongueLine",width:1.6},tooth,...a.lips[kind]);
 shapes.push({part:"airflow",d:a.airs[kind],fill:null,stroke:"air",width:2.5});
 const end=kind==="w"?451:kind==="v"?438:441,y=kind==="v"?322:kind==="th"?329:330;
 shapes.push({part:"airflow-tip",d:`M${end-9} ${y-5} L${end} ${y} L${end-9} ${y+5}`,stroke:"air",width:2.5});
 shapes.push({part:"vocal-folds",d:voiced?"M224 420 L231 422 M235 422 L242 420":"M224 417 L230 423 M236 423 L242 417",stroke:"voice",width:2.3});
 if(voiced)shapes.push({part:"voicing",d:"M225 408 Q229 403 232 408 M235 408 Q239 403 242 408 M225 436 Q229 441 232 436 M235 436 Q239 441 242 436",stroke:"voice",width:1.8});
 return shapes;
}
function svg(title,desc,shapes,view=[0,0,520,500],commonCount=14){
 const a=load("art");const dark={paper:"#182126",skin:"#293238",ink:"#d1d8d9",soft:"#94817c",cavity:"#1c282e",tongue:"#c58989",tongueLine:"#e1aaaa",air:"#7bbcd0",voice:"#bea2cb",tooth:"#ecedf0"};
 const esc=s=>String(s).replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;");
 const props=p=>Object.entries(p).map(([k,v])=>`--ar-${k}:${v}`).join(";");
 const path=s=>`<path data-part="${esc(s.part)}" d="${esc(s.d)}" fill="${s.fill?`var(--ar-${s.fill},${a.palette[s.fill]})`:"none"}" stroke="${s.stroke?`var(--ar-${s.stroke},${a.palette[s.stroke]})`:"none"}" stroke-width="${s.width||1.5}"${s.transform?` transform="matrix(${s.transform[0]} 0 0 ${s.transform[1]} ${s.transform[2]} ${s.transform[3]})"`:""}/>`;
 return `<svg xmlns="http://www.w3.org/2000/svg" class="articulation-redraw" viewBox="${view.join(" ")}" role="img" aria-label="${esc(desc)}" stroke-linecap="round" stroke-linejoin="round">
<title>${esc(title)}</title><desc>${esc(desc)}</desc>
<style>.articulation-redraw{${props(a.palette)}}@media(prefers-color-scheme:dark){.articulation-redraw{${props(dark)}}}[data-theme="light"] .articulation-redraw{${props(a.palette)}}[data-theme="dark"] .articulation-redraw{${props(dark)}}</style>
<g data-part="fixed-anatomy">${shapes.slice(0,commonCount).map(path).join("\n")}</g>
<g data-part="articulators">${shapes.slice(commonCount).map(path).join("\n")}</g>
</svg>\n`;
}
function lettering(s,x,y,k=3.1){
 const chars=load("font");return Array.from(s,(c,i)=>chars[c]?{part:"label",label:c,d:chars[c],fill:null,stroke:"ink",width:.36,transform:[k,k,x+i*k*6,y]}:null).filter(Boolean);
}
function flatten(d){
 const t=d.match(/[A-Za-z]|-?\d*\.?\d+(?:e[-+]?\d+)?/g);let i=0,c="",p=[0,0],start=null,arr=[],sub=null;
 const add=q=>{p=q;sub.push(q);};const n=()=>Number(t[i++]);
 while(i<t.length){if(/[A-Za-z]/.test(t[i]))c=t[i++];switch(c){
 case"M":p=[n(),n()];start=p;sub=[p];arr.push(sub);c="L";break;
 case"L":add([n(),n()]);break;
 case"C":{const p0=p,p1=[n(),n()],p2=[n(),n()],p3=[n(),n()];for(let s=1;s<=24;s++){const q=s/24,u=1-q;add([u*u*u*p0[0]+3*u*u*q*p1[0]+3*u*q*q*p2[0]+q*q*q*p3[0],u*u*u*p0[1]+3*u*u*q*p1[1]+3*u*q*q*p2[1]+q*q*q*p3[1]]);}break;}
 case"Q":{const p0=p,p1=[n(),n()],p2=[n(),n()];for(let s=1;s<=20;s++){const q=s/20,u=1-q;add([u*u*p0[0]+2*u*q*p1[0]+q*q*p2[0],u*u*p0[1]+2*u*q*p1[1]+q*q*p2[1]]);}break;}
 case"Z":add(start);c="";break;default:throw Error("Unsupported path "+c);
 }}
 return arr;
}
function raster(shapes,width=780,height=750,dark=false,view=[0,0,520,500]){
 const a=load("art");const palette=dark?{paper:"#182126",skin:"#293238",ink:"#d1d8d9",soft:"#94817c",cavity:"#1c282e",tongue:"#c58989",tongueLine:"#e1aaaa",air:"#7bbcd0",voice:"#bea2cb",tooth:"#ecedf0"}:a.palette;
 const k=2,w=width*k,h=height*k,pix=new Uint8Array(w*h*3),scale=w/view[2];
 const col=s=>{const h=palette[s]||s;return[parseInt(h.slice(1,3),16),parseInt(h.slice(3,5),16),parseInt(h.slice(5,7),16)];};
 const bg=col("paper");for(let i=0;i<pix.length;i+=3){pix[i]=bg[0];pix[i+1]=bg[1];pix[i+2]=bg[2];}
 const paint=(x,y,c)=>{if(x>=0&&y>=0&&x<w&&y<h){const at=(y*w+x)*3;pix[at]=c[0];pix[at+1]=c[1];pix[at+2]=c[2];}};
 for(const s of shapes){
   const tr=s.transform||[1,1,0,0];const polys=flatten(s.d).map(ps=>ps.map(p=>[(p[0]*tr[0]+tr[2]-view[0])*scale,(p[1]*tr[1]+tr[3]-view[1])*scale]));
   if(s.fill){const c=col(s.fill),all=polys.flat(),minY=Math.max(0,Math.floor(Math.min(...all.map(p=>p[1])))),maxY=Math.min(h-1,Math.ceil(Math.max(...all.map(p=>p[1]))));
    for(let y=minY;y<=maxY;y++){let xs=[];for(const ps of polys)for(let i=0;i<ps.length;i++){const a=ps[i],b=ps[(i+1)%ps.length],yy=y+.5;if((a[1]>yy)!==(b[1]>yy))xs.push(a[0]+(yy-a[1])*(b[0]-a[0])/(b[1]-a[1]));}
     xs.sort((a,b)=>a-b);for(let j=0;j+1<xs.length;j+=2)for(let x=Math.max(0,Math.ceil(xs[j]-.5));x<Math.min(w,xs[j+1]-.5);x++)paint(x,y,c);
    }
   }
   if(s.stroke){const c=col(s.stroke),r=(s.width||1.5)*scale*Math.sqrt(Math.abs(tr[0]*tr[1]))/2,rr=r*r;for(const ps of polys)for(let i=1;i<ps.length;i++){const a=ps[i-1],b=ps[i],dx=b[0]-a[0],dy=b[1]-a[1],ll=dx*dx+dy*dy;
     const x0=Math.max(0,Math.floor(Math.min(a[0],b[0])-r)),x1=Math.min(w-1,Math.ceil(Math.max(a[0],b[0])+r)),y0=Math.max(0,Math.floor(Math.min(a[1],b[1])-r)),y1=Math.min(h-1,Math.ceil(Math.max(a[1],b[1])+r));
     for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++){const q=ll?Math.max(0,Math.min(1,((x+.5-a[0])*dx+(y+.5-a[1])*dy)/ll)):0;const ex=x+.5-a[0]-q*dx,ey=y+.5-a[1]-q*dy;if(ex*ex+ey*ey<=rr)paint(x,y,c);}
    }
   }
 }
 const raw=new Uint8Array(height*(width*3+1));for(let y=0;y<height;y++){let at=y*(width*3+1)+1;for(let x=0;x<width;x++)for(let c=0;c<3;c++){let sum=0;for(let yy=0;yy<k;yy++)for(let xx=0;xx<k;xx++)sum+=pix[((y*k+yy)*w+x*k+xx)*3+c];raw[at++]=Math.round(sum/(k*k));}}
 return {raw,width,height};
}
function png(data){
 const {raw,width,height}=data;
 const lb=[3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258],le=[0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0],db=[1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577],de=[0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13];
 const out=[0x78,0x01];let buf=0,nb=0;
 const bits=(v,n)=>{buf|=v<<nb;nb+=n;while(nb>=8){out.push(buf&255);buf>>>=8;nb-=8;}};
 const rev=(v,n)=>{let r=0;while(n--){r=(r<<1)|(v&1);v>>>=1;}return r;};
 const symbol=s=>{if(s<144)bits(rev(0x30+s,8),8);else if(s<256)bits(rev(0x190+s-144,9),9);else if(s<280)bits(rev(s-256,7),7);else bits(rev(0xc0+s-280,8),8);};
 bits(3,3);const last=new Map();const key=i=>(raw[i]<<16)|(raw[i+1]<<8)|raw[i+2];
 let p=0;while(p<raw.length){let len=0,dist=0;if(p+3<raw.length){const k=key(p),prev=last.get(k);last.set(k,p);if(prev!==undefined&&p-prev<=32768){const max=Math.min(258,raw.length-p);while(len<max&&raw[prev+len]===raw[p+len])len++;dist=p-prev;}}
 if(len>=4){let li=0;while(li+1<lb.length&&lb[li+1]<=len)li++;symbol(257+li);bits(len-lb[li],le[li]);let di=0;while(di+1<db.length&&db[di+1]<=dist)di++;bits(rev(di,5),5);bits(dist-db[di],de[di]);for(let j=1;j<len&&p+j+2<raw.length;j++)last.set(key(p+j),p+j);p+=len;}else{symbol(raw[p++]);}}
 symbol(256);if(nb)out.push(buf&255);
 let a=1,b=0;for(const x of raw){a=(a+x)%65521;b=(b+a)%65521;}out.push(b>>>8,b&255,a>>>8,a&255);
 const u32=n=>[(n>>>24)&255,(n>>>16)&255,(n>>>8)&255,n&255];
 const crc=bytes=>{let c=0xffffffff;for(const b of bytes){c^=b;for(let k=0;k<8;k++)c=(c>>>1)^((c&1)?0xedb88320:0);}return(c^0xffffffff)>>>0;};
 const chunk=(s,bytes)=>{const t=Array.from(s,c=>c.charCodeAt(0)),payload=[...t,...bytes];return[...u32(bytes.length),...payload,...u32(crc(payload))];};
 const header=[...u32(width),...u32(height),8,2,0,0,0];
 const bytes=Uint8Array.from([137,80,78,71,13,10,26,10,...chunk("IHDR",header),...chunk("IDAT",out),...chunk("IEND",[])]);
 const alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";let s="";for(let i=0;i<bytes.length;i+=3){const v=(bytes[i]<<16)|((bytes[i+1]||0)<<8)|(bytes[i+2]||0);s+=alphabet[(v>>>18)&63]+alphabet[(v>>>12)&63]+(i+1<bytes.length?alphabet[(v>>>6)&63]:"=")+(i+2<bytes.length?alphabet[v&63]:"=");}
 return s;
}
const root=fileURLToPath(new URL("../",import.meta.url));
const check=process.argv.includes("--check");
const write=(path,content)=>{ const target=join(root,path); if(check){if(readFileSync(target,"utf8")!==content)throw new Error("Stale SVG: "+path);}else{mkdirSync(dirname(target),{recursive:true});writeFileSync(target,content);} };
for(const [name,[title,desc]] of Object.entries(state.meta)){
 const front=name.startsWith("front-"),shapes=front?state.fronts[name]:geometry(name);
 write("static/img/articulation/"+name+".svg",svg(title,desc,shapes,front?[0,0,100,125]:[0,0,520,500],front?0:14));
}
const labelled=[...geometry("v"),
 {part:"label-line",d:"M452 300 L421 300 L383 315 M452 355 L425 355 L395 338 M452 403 L397 403 L314 370",stroke:"ink",width:1},
 ...lettering("ЗУБЫ",460,284),...lettering("ГУБЫ",460,341),...lettering("ЯЗЫК",460,389),
 {part:"voice-badge",d:"M266 458 Q270 454 274 458 Q278 462 282 458 M266 463 Q270 459 274 463 Q278 467 282 463 M266 468 Q270 464 274 468 Q278 472 282 468",stroke:"voice",width:1.8},
 ...lettering("ГОЛОС ЕСТЬ",293,455,2.3)
];
write("docs/articulation-redraw/v-labelled.svg",svg("Новая схема V с подписями","Голова сбоку в разрезе. Подписаны зубы, губы и язык. Верхние зубы касаются нижней губы. Голос есть.",labelled,[0,0,680,500]));
write("docs/articulation-redraw/v-mouth-detail.svg",svg(...state.meta.v,geometry("v"),[347,292,100,75]));
if(process.argv.includes("--preview")&&!check){
 const put=(path,bytes)=>{mkdirSync(dirname(join(root,path)),{recursive:true});writeFileSync(join(root,path),Buffer.from(bytes,"base64"));};
 for(const [name,dark] of [["v-labelled-light",false],["v-labelled-dark",true]])put("docs/articulation-redraw/"+name+".png",png(raster(labelled,884,650,dark,[0,0,680,500])));
 put("docs/articulation-redraw/v-mouth-detail.png",png(raster(geometry("v"),640,480,false,[347,292,100,75])));
 for(const name of Object.keys(state.meta)){const front=name.startsWith("front-");put("docs/articulation-redraw/renders/"+name+".png",png(raster(front?state.fronts[name]:geometry(name),front?300:416,front?375:400,false,front?[0,0,100,125]:[0,0,520,500])));}
}
console.log(check?"SVG sources match.":"Original articulation assets generated.");
