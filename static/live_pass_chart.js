// Preview prototype: measured endpoints only, never infer positions or QB interceptions.
(function(root){
    'use strict';
    const PASS=['pass_complete','pass_incomplete','passing_touchdown'];
    const LOCATED=[...PASS,'interception'];
    const COLORS={pass_complete:'#67eb8b',pass_incomplete:'#e4edf7',passing_touchdown:'#52aaff',interception:'#ff687c'};
    const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const valid=l=>l && ['start_x','start_y','end_x','end_y'].every(k=>Number.isInteger(l[k])&&l[k]>=0&&l[k]<=100);
    const point=(x,y)=>{const t=y/100;return [150-130*t+x/100*(300+260*t),35+325*t];};
    function fieldBase(){
        return `<path fill="#12242c" stroke="#82939d" d="M150 35 H450 L580 360 H20 Z"/><path fill="#203847" d="M150 35 H450 L463 68 H137 Z M33 327 H567 L580 360 H20 Z"/>${[10,20,30,40,50,60,70,80,90].map(y=>{const a=point(0,y),b=point(100,y);return `<path stroke="#51666e" stroke-width="1" d="M${a} L${b}"/>`;}).join('')}<path stroke="#47565f" stroke-dasharray="3 5" d="M300 35 V360"/><text fill="#a4b6c6" text-anchor="middle" x="300" y="24" font-size="13">ATAQUE ↑</text>`;
    }
    function passSummary(events){
        const rows=new Map();
        for(const e of events){if(e.voided_at || !PASS.includes(e.kind))continue;const key=`${e.team_id}:${e.player_id}`;
            if(!rows.has(key))rows.set(key,{key,team_id:e.team_id,label:e.player_label||'Pasador',attempts:0,completed:0,td:0});
            const r=rows.get(key);r.attempts++;if(e.kind!=='pass_incomplete')r.completed++;if(e.kind==='passing_touchdown')r.td++;
        }
        return [...rows.values()];
    }
    function mapMarkup(events,selected){
        let paths='';
        for(const e of events){const l=e.field_location;if(!valid(l))continue;const a=point(l.start_x,l.start_y),b=point(l.end_x,l.end_y);const active=e.id===selected;
            const control=[(a[0]+b[0])/2,Math.min(a[1],b[1])-35];
            if(active)paths+=`<path class="live-pass-trajectory" fill="none" stroke="${COLORS[e.kind]}" stroke-width="3" d="M${a} Q${control} ${b}"/><circle cx="${a[0]}" cy="${a[1]}" r="5" fill="#ffd456"/>`;
            paths+=`<g class="live-pass-marker" data-pass-id="${Number(e.id)}" tabindex="0" role="button" aria-label="${esc(e.player_label)}: ${esc(e.kind==='pass_incomplete'?'pase incompleto':e.kind==='passing_touchdown'?'touchdown':e.kind==='interception'?'intercepción defensiva':'pase completo')}"><circle cx="${b[0]}" cy="${b[1]}" r="16" fill="transparent"/><circle cx="${b[0]}" cy="${b[1]}" r="${active?8:6}" stroke="${COLORS[e.kind]}" stroke-width="3" fill="${e.kind==='pass_incomplete'?'#12242c':COLORS[e.kind]}"/></g>`;
        }
        return `<svg viewBox="0 0 600 390" role="group" aria-label="Mapa de ubicaciones aproximadas de pases capturados">${fieldBase()}${paths}</svg>`;
    }
    function locationMarkup(event,animated){
        const l=event.field_location,a=point(l.start_x,l.start_y),b=point(l.end_x,l.end_y);const td=['touchdown','passing_touchdown'].includes(event.kind);
        const path=event.kind==='touchdown'?`M ${a} L ${b}`:`M ${a} Q ${(a[0]+b[0])/2} ${Math.min(a[1],b[1])-35} ${b}`;
        return `<svg viewBox="0 0 600 390" role="img" aria-label="Ubicación aproximada capturada por el árbitro">${fieldBase()}<path class="live-field-route ${animated?'live-field-draw':''}" fill="none" stroke="${COLORS[event.kind]||'#ffd456'}" d="${path}"/><circle cx="${a[0]}" cy="${a[1]}" r="9" fill="#ffd456"/><circle cx="${b[0]}" cy="${b[1]}" r="9" fill="${COLORS[event.kind]||'#ffd456'}"/><g class="live-field-ball" ${animated?'':`transform="translate(${b})"`}><ellipse rx="12" ry="7"/><path d="M -5 0 H 5 M -3 -3 V 3 M 0 -3 V 3 M 3 -3 V 3"/>${animated?`<animateMotion dur="1.3s" repeatCount="1" fill="freeze" path="${path}"/>`:''}</g></svg>${td?'<div class="live-field-banner live-field-td"><strong>¡TOUCHDOWN!</strong><span>+6 puntos confirmados</span></div>':''}`;
    }
    class LivePassChart{
        constructor(panel,onSelect){this.panel=panel;this.onSelect=onSelect;this.filter=panel.querySelector('#live-chart-passer');this.selected=null;this.data=null;
            this.filter.addEventListener('change',()=>{this.selected=null;this.render();});
            const select=e=>{const marker=e.target.closest('[data-pass-id]');if(!marker)return;this.selected=Number(marker.dataset.passId);this.render();this.onSelect(this.selected);};
            panel.querySelector('#live-pass-map').addEventListener('click',select);
            panel.querySelector('#live-pass-map').addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(e);}});
        }
        update(data){this.data=data;this.render();}
        render(){if(!this.data)return;const events=(this.data.events||[]).filter(e=>!e.voided_at);const summaries=passSummary(events);const old=this.filter.value;
            this.filter.innerHTML='<option value="">Todos los jugadores</option>'+summaries.map(r=>`<option value="${r.key}">${esc(r.label)} · ${esc(r.team_id===this.data.home_team.id?this.data.home_team.name:this.data.away_team.name)}</option>`).join('');
            this.filter.value=summaries.some(r=>r.key===old)?old:'';const filter=this.filter.value;
            const selectedRows=summaries.filter(r=>!filter||r.key===filter);
            this.panel.querySelector('#live-pass-summary').innerHTML=selectedRows.length?selectedRows.map(r=>`<article><strong>${esc(r.label)}</strong><small>${esc(r.team_id===this.data.home_team.id?this.data.home_team.name:this.data.away_team.name)}</small><div><span><b>${r.completed}/${r.attempts}</b>Completos / intentos</span><span><b>${(r.completed/r.attempts*100).toFixed(1)}%</b>Efectividad</span><span><b>${r.td}</b>TD por pase</span></div></article>`).join(''):'<p class="form-help">El resumen del pasador aparecerá con sus primeras capturas confirmadas.</p>';
            const candidates=events.filter(e=>LOCATED.includes(e.kind)&&(!filter||`${e.team_id}:${e.player_id}`===filter));const located=candidates.filter(e=>valid(e.field_location));
            if(!located.some(e=>e.id===this.selected))this.selected=located.at(-1)?.id??null;
            this.panel.querySelector('#live-pass-map').innerHTML=mapMarkup(located,this.selected);
            this.panel.querySelector('#live-map-count').textContent=`${located.length} de ${candidates.length} jugadas con ubicación. ${located.length?'Toca un punto para repetir la jugada.':'El mapa se llenará cuando el árbitro marque salida y llegada.'} Las intercepciones identifican al defensor; no se atribuyen al pasador.`;
        }
    }
    const LiveLocationCapture={
        panel:null, values:[],
        init(){this.panel=root.document?.querySelector('#live-location-panel');if(!this.panel)return;
            this.inputs=['start-x','start-y','end-x','end-y'].map(k=>root.document.querySelector('#location-'+k));
            this.editor=root.document.querySelector('#live-location-editor');
            this.editor.addEventListener('click',e=>{const bounds=this.editor.getBoundingClientRect();const x=Math.round(Math.max(0,Math.min(100,(e.clientX-bounds.left)/bounds.width*100)));const y=Math.round(Math.max(0,Math.min(100,(e.clientY-bounds.top)/bounds.height*100)));const offset=this.inputs[0].value!==''&&this.inputs[1].value!==''?2:0;this.inputs[offset].value=x;this.inputs[offset+1].value=y;this.draw();});
            this.inputs.forEach(input=>input.addEventListener('input',()=>this.draw()));
            root.document.querySelector('#live-location-reset').addEventListener('click',()=>this.reset());this.draw();
        },
        draw(){const vals=this.inputs.map(i=>i.value===''?null:Number(i.value));this.editor.innerHTML='<span class="live-location-arrow">ATAQUE ↑</span>'+[0,2].map((i)=>vals[i]!==null&&vals[i+1]!==null?`<span class="live-location-dot" style="left:${Math.max(0,Math.min(100,vals[i]))}%;top:${Math.max(0,Math.min(100,vals[i+1]))}%">${i?'2':'1'}</span>`:'').join('');root.document.querySelector('#live-location-status').textContent=vals.every(v=>v!==null)?'Salida y llegada listas. Pulsa Registrar jugada.':vals[0]!==null?'Ahora marca la llegada.':'Marca la salida del balón.';},
        read(kind){if(!this.panel?.open)return null;if(![...PASS,'touchdown','interception'].includes(kind))return null;const vals=this.inputs.map(i=>i.value===''?null:Number(i.value));const l=Object.fromEntries(['start_x','start_y','end_x','end_y'].map((k,i)=>[k,vals[i]]));return valid(l)?l:false;},
        reset(){if(!this.panel)return;this.inputs.forEach(i=>i.value='');this.draw();},
        restore(l){if(!this.panel)return;this.reset();this.panel.open=valid(l);if(valid(l)){['start_x','start_y','end_x','end_y'].forEach((k,i)=>this.inputs[i].value=l[k]);this.draw();}}
    };
    root.fieldLocationMarkup=(event,animated)=>valid(event?.field_location)?locationMarkup(event,animated):null;
    root.LivePassChart=LivePassChart;root.LiveLocationCapture=LiveLocationCapture;
    if(root.document)LiveLocationCapture.init();
    if(typeof module!=='undefined'&&module.exports)module.exports={passSummary,mapMarkup,valid,point};
})(typeof globalThis!=='undefined'?globalThis:window);
