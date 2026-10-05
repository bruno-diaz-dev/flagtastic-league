// Statistical illustration only: geometry is decorative, never measured play data.
(function(root){
    'use strict';
    const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    function totals(row){
        const attempts=Math.max(0,Number(row.attempts)||0);
        const completed=Math.max(0,Math.min(attempts,Number(row.completed)||0));
        return {attempts,completed,incomplete:attempts-completed,percentage:attempts?completed/attempts*100:0};
    }
    function markerLayout(row){
        const t=totals(row||{}),count=Math.min(t.attempts,45);
        const completed=count===t.attempts?t.completed:Math.round(count*t.percentage/100);
        let seed=((Number(row?.player_id)||1)*9301+(Number(row?.team_id)||1)*49297)>>>0;
        const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
        const locations=[];
        for(let i=0;i<count;i++){
            let x,y;
            for(let tries=0;tries<30;tries++){
                x=9+random()*82;y=10+Math.pow(random(),.55)*78;
                if(!locations.some(p=>Math.hypot((p.x-x)*.8,p.y-y)<5))break;
            }
            locations.push({x,y,complete:i<completed});
        }
        return locations;
    }
    function fieldMarkup(row){
        const t=totals(row||{}),locations=markerLayout(row);
        const point=(x,y)=>{const depth=y/100;return [215-192*depth+x/100*(530+384*depth),16+492*depth];};
        const edge=y=>[point(0,y),point(100,y)];
        const horizontal=Array.from({length:51},(_,i)=>{const [a,b]=edge(i*2);return `<path stroke="${i%5===0?'#626975':'#3d444f'}" stroke-width="${i%5===0?1.4:.65}" d="M${a} L${b}"/>`;}).join('');
        const vertical=Array.from({length:27},(_,i)=>`<path stroke="#3e4551" stroke-width=".7" d="M${point(i/26*100,0)} L${point(i/26*100,100)}"/>`).join('');
        const hashes=Array.from({length:50},(_,i)=>[47.5,52.5].map(x=>`<path stroke="#8a929f" opacity=".65" stroke-width="1.6" d="M${point(x-1,i*2)} L${point(x+1,i*2)}"/>`).join('')).join('');
        const labels=[8,22,36,50,64].map((y,i)=>{const [a,b]=edge(y);return `<text x="${a[0]-7}" y="${a[1]+5}" text-anchor="end">+${50-i*10}</text><text x="${b[0]+7}" y="${b[1]+5}">+${50-i*10}</text>`;}).join('');
        const los=edge(74);
        const markers=locations.map((p,i)=>{const [x,y]=point(p.x,p.y);const rx=7+7*p.y/100,ry=rx*.48,c=p.complete?'#8bff31':'#f5f6fa';return `<g class="passing-marker" data-result="${p.complete?'complete':'incomplete'}"><ellipse cx="${x}" cy="${y+3}" rx="${rx+3}" ry="${ry+2}" fill="#000" opacity=".65"/><ellipse cx="${x}" cy="${y}" rx="${rx}" ry="${ry}" fill="${p.complete?'#385724':'#262c36'}" stroke="${c}" stroke-width="2.8"/><ellipse cx="${x}" cy="${y}" rx="${rx*.45}" ry="${ry*.45}" fill="${p.complete?'#8bff31':'#e9edf5'}" opacity=".6"/></g>`;}).join('');
        const destination=locations.find(p=>p.complete)||locations[0];
        const end=destination?point(destination.x,destination.y):null;
        const arc=end?`<path d="M480 477 Q${end[0]-40} ${Math.min(end[1],260)-150} ${end}" fill="none" stroke="#115fad" stroke-width="18" opacity=".75" stroke-linecap="round"/><path d="M480 477 Q${end[0]-40} ${Math.min(end[1],260)-150} ${end}" fill="none" stroke="#238deb" stroke-width="5" opacity=".55"/><ellipse cx="${end[0]}" cy="${end[1]}" rx="12" ry="6" fill="${destination.complete?'#385724':'#262c36'}" stroke="${destination.complete?'#8bff31':'#f5f6fa'}" stroke-width="3"/>`:'';
        return `<svg viewBox="0 0 960 540" role="img" aria-label="${esc('Campo ilustrativo, '+t.completed+' completos de '+t.attempts+' intentos. Posiciones y escala decorativas.')}"><defs><linearGradient id="pass-turf" x2="0" y2="1"><stop stop-color="#262d39"/><stop offset="1" stop-color="#151b25"/></linearGradient></defs><path d="M195 16 H765 L958 508 H2 Z" fill="#727d89"/><path d="M215 16 H745 L937 508 H23 Z" fill="url(#pass-turf)"/>${horizontal}${vertical}${hashes}<g fill="#e3e6eb" font-size="19" font-weight="700">${labels}</g><path d="M${los[0]} L${los[1]}" stroke="#187af5" stroke-width="5"/>${markers}${arc}<g fill="#dbe9ff" font-size="20" font-weight="800"><text x="24" y="${los[0][1]-9}">LOS</text><text x="902" y="${los[1][1]-9}">LOS</text></g><text x="480" y="533" text-anchor="middle" fill="#8d9baa" font-size="13">POSICIONES Y ESCALA ILUSTRATIVAS</text></svg>`;
    }
    class PassingStatisticsView{
        constructor(panel){this.panel=panel;this.select=panel.querySelector('#passing-visual-player');this.rows=[];this.request=0;this.select.addEventListener('change',()=>this.render());}
        async load(branch,category){
            const request=++this.request;this.rows=[];this.select.disabled=true;
            this.select.innerHTML='<option>Cargando pasadores…</option>';this.render();
            const status=this.panel.querySelector('#passing-visual-status');status.textContent='Consultando estadísticas…';
            try{
                const response=await fetch('/api/statistics/passing-visual?'+new URLSearchParams({branch,category}));
                if(!response.ok)throw new Error('Request failed');
                const rows=await response.json();if(request!==this.request)return;
                this.rows=rows;this.select.innerHTML=rows.length?rows.map((r,i)=>'<option value="'+i+'">#'+Number(r.jersey_number)+' '+esc(r.display_name)+' · '+esc(r.team_name)+'</option>').join(''):'<option>Sin pasadores registrados</option>';
                this.select.disabled=!rows.length;this.render();status.textContent=rows.length?'':'Sin estadísticas de pases publicadas para esta división.';
            }catch(error){if(request!==this.request)return;this.select.innerHTML='<option>No se pudo cargar</option>';status.textContent='No se pudo cargar la visualización. Vuelve a consultar las estadísticas.';}
        }
        render(){
            const row=this.rows[Number(this.select.value)]||this.rows[0],t=totals(row||{});
            this.panel.querySelector('#passing-visual-identity').innerHTML=row?`<div class="passing-player-photo">${row.profile_photo_url?`<img src="${esc(row.profile_photo_url)}" alt="Foto de ${esc(row.display_name)}" loading="lazy">`:`<span>${esc(row.display_name.trim().split(/\s+/).slice(0,2).map(w=>w[0]).join(''))}</span>`}<b>#${Number(row.jersey_number)} · QB</b></div><div class="passing-player-name"><strong>${esc(row.display_name)}</strong><span>${esc(row.team_name)}</span></div>`:'';
            this.panel.querySelector('#passing-visual-summary').innerHTML=row?'<span><strong>'+t.completed+'/'+t.attempts+'</strong>Completos / intentos</span><span><strong>'+t.percentage.toFixed(1)+'%</strong>Efectividad</span><span><strong>'+t.incomplete+'</strong>Incompletos</span>':'';
            this.panel.querySelector('#passing-visual-field').innerHTML=fieldMarkup(row);
            this.panel.querySelector('#passing-visual-note').textContent=row?`${t.attempts>45?'Muestra de 45 de '+t.attempts+' intentos. ':''}Ubicaciones ilustrativas · cifras oficiales.`:'Sin intentos registrados.';
        }
    }
    root.PassingStatisticsView=PassingStatisticsView;
    if(typeof module!=='undefined'&&module.exports)module.exports={totals,fieldMarkup,markerLayout};
})(typeof globalThis!=='undefined'?globalThis:window);

