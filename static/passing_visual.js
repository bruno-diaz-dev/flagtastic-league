// Statistical illustration only: geometry is decorative, never measured play data.
(function(root){
    'use strict';
    const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    function totals(row){
        const attempts=Math.max(0,Number(row.attempts)||0);
        const completed=Math.max(0,Math.min(attempts,Number(row.completed)||0));
        return {attempts,completed,incomplete:attempts-completed,percentage:attempts?completed/attempts*100:0};
    }
    function fieldMarkup(row){
        const t=totals(row||{}),count=t.attempts?40:0,completeDots=Math.round(count*t.percentage/100);
        const point=(x,y)=>{const depth=y/100;return [150-130*depth+x/100*(300+260*depth),35+325*depth];};
        const markers=Array.from({length:count},(_,i)=>{
            // Uniform decorative grid; no relation to actual throws, yardage or direction.
            const x=13+(i%8)*10.5,y=20+Math.floor(i/8)*15;
            const p=point(x,y),complete=i<completeDots;
            return '<circle cx="'+p[0]+'" cy="'+p[1]+'" r="6" stroke="'+(complete?'#67eb8b':'#e4edf7')+'" stroke-width="2.5" fill="'+(complete?'#67eb8b':'#12242c')+'"/>';
        }).join('');
        const lines=[10,20,30,40,50,60,70,80,90].map(y=>'<path stroke="#50656e" d="M'+point(0,y)+' L'+point(100,y)+'"/>').join('');
        return '<svg viewBox="0 0 600 400" role="img" aria-label="'+esc('Campo ilustrativo: '+t.completed+' completos de '+t.attempts+' intentos. Posiciones decorativas.')+'"><path fill="#12242c" stroke="#82939d" d="M150 35 H450 L580 360 H20 Z"/><path fill="#203847" d="M150 35 H450 L463 68 H137 Z M33 327 H567 L580 360 H20 Z"/>'+lines+'<path stroke="#47565f" stroke-dasharray="3 5" d="M300 35 V360"/>'+markers+(count?'<path d="M300 315 Q250 140 365 100" fill="none" stroke="#52aaff" stroke-width="4" opacity=".8"/>':'')+'<text x="300" y="385" text-anchor="middle" font-size="13" fill="#a9bbd3">VISTA ILUSTRATIVA · SIN UBICACIONES REALES</text></svg>';
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
                this.select.disabled=!rows.length;this.render();status.textContent=rows.length?'Totales oficiales acumulados. La ilustración no requiere capturar ubicaciones.':'Sin estadísticas de pases publicadas para esta división.';
            }catch(error){if(request!==this.request)return;this.select.innerHTML='<option>No se pudo cargar</option>';status.textContent='No se pudo cargar la visualización. Vuelve a consultar las estadísticas.';}
        }
        render(){
            const row=this.rows[Number(this.select.value)]||this.rows[0],t=totals(row||{});
            this.panel.querySelector('#passing-visual-summary').innerHTML=row?'<span><strong>'+t.completed+'/'+t.attempts+'</strong>Completos / intentos</span><span><strong>'+t.percentage.toFixed(1)+'%</strong>Efectividad</span><span><strong>'+t.incomplete+'</strong>Incompletos</span>':'';
            this.panel.querySelector('#passing-visual-field').innerHTML=fieldMarkup(row);
        }
    }
    root.PassingStatisticsView=PassingStatisticsView;
    if(typeof module!=='undefined'&&module.exports)module.exports={totals,fieldMarkup};
})(typeof globalThis!=='undefined'?globalThis:window);
