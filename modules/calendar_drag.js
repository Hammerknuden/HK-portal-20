export default function(component) {
    const {data, parentElement, setTriggerValue} = component;
    const host = parentElement.querySelector('#calendar-drag');
    host.replaceChildren();
    const toolbar = document.createElement('div');
    host.append(toolbar);
    const scroller = document.createElement('div');
    scroller.className = 'scroll';
    host.append(scroller);
    const ns = 'http://www.w3.org/2000/svg';
    const day = 86400000, start = Date.parse(data.start), end = Date.parse(data.end);
    let scale = 24;
    function draw() {
        scroller.replaceChildren();
        const width = Math.max(600, 110 + (end - start) / day * scale);
        const svg = document.createElementNS(ns, 'svg');
        svg.setAttribute('width', width); svg.setAttribute('height', 445);
        scroller.append(svg);
        function el(tag, attrs, text, parent=svg) {
            const node = document.createElementNS(ns, tag);
            for (const [k,v] of Object.entries(attrs)) node.setAttribute(k,v);
            if (text !== undefined) node.textContent = text;
            parent.append(node); return node;
        }
        const x = date => 110 + (Date.parse(date) - start) / day * scale;
        for (let t=start; t<=end; t+=day) {
            const d=new Date(t), pos=110+(t-start)/day*scale;
            if (d.getUTCDay() === 1) {
                const thursday=new Date(t); thursday.setUTCDate(d.getUTCDate()+3);
                const week=Math.ceil(((thursday-new Date(Date.UTC(thursday.getUTCFullYear(),0,1)))/day+1)/7);
                el('line',{x1:pos,x2:pos,y1:40,y2:425,stroke:'#ddd'});
                el('text',{x:pos+2,y:15,fill:'#555'},`Uge ${week}`);
                el('text',{x:pos+2,y:32,fill:'#555'},d.toISOString().slice(5,10));
            }
        }
        for (const [room,label] of Object.entries(data.rooms)) {
            const y=40+(Number(room)-1)*55;
            el('rect',{x:0,y,width:110,height:55,fill:'#f4f4f4'});
            el('text',{x:8,y:y+32,fill:'#222'},label);
            el('line',{x1:0,x2:width,y1:y+55,y2:y+55,stroke:'#ddd'});
        }
        const today = new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Copenhagen'}).format(new Date());
        if (x(today)>=110 && x(today)<=width) el('line',{x1:x(today),x2:x(today),y1:40,y2:425,stroke:'red'});
        for (const b of data.items) {
            if (Date.parse(b.end)<=start || Date.parse(b.start)>=end) continue;
            const left=Math.max(110,x(b.start)), right=Math.min(width,x(b.end));
            const g=el('g',{'data-booking':b.id,transform:`translate(0,${(b.room-1)*55})`,
                style:`cursor:${b.locked?'not-allowed':'grab'}`});
            el('rect',{x:left,y:49,width:Math.max(2,right-left),height:35,rx:3,fill:b.color},undefined,g);
            if (right-left>25) el('text',{x:left+4,y:71,fill:'white','pointer-events':'none'},`${b.locked?'🔒 ':''}${b.label}`,g);
            el('title',{},`${b.label} · ${b.name}\n${b.start} → ${b.end}${b.locked?' · Låst':''}`,g);
            if (b.locked) continue;
            let dragging=false, origin=0;
            g.onpointerdown=e=>{if(e.button!==0)return;dragging=true;origin=e.clientY;g.setPointerCapture(e.pointerId);g.style.opacity='.65';};
            g.onpointermove=e=>{if(dragging)g.setAttribute('transform',`translate(0,${(b.room-1)*55+e.clientY-origin})`);};
            const reset=()=>{dragging=false;g.style.opacity='1';g.setAttribute('transform',`translate(0,${(b.room-1)*55})`);};
            g.onpointercancel=reset;
            g.onlostpointercapture=reset;
            g.onpointerup=e=>{
                if(!dragging)return;
                const rect=svg.getBoundingClientRect(), y=e.clientY-rect.top, px=e.clientX-rect.left;
                const room=Math.floor((y-40)/55)+1;
                if(y>=40 && y<425 && px>=110 && px<=width && room!==b.room) {
                    // Keep the accepted drop visible while Python processes the move.
                    b.room=room;
                    reset();
                    setTriggerValue('move',{id:b.id,room});
                } else {
                    reset();
                }
            };
        }
    }
    for (const [label,value] of [['Årsoversigt',3],['Uger',24],['Dage',48]]) {
        const button=document.createElement('button'); button.textContent=label;
        button.onclick=()=>{scale=value;draw();}; toolbar.append(button);
    }
    draw();
    return ()=>host.replaceChildren();
}
