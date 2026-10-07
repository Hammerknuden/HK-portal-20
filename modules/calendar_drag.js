export default function(component) {
    const {data, parentElement, setTriggerValue, setStateValue} = component;
    const Plotly = window.Plotly;
    const host = parentElement.querySelector('.calendar-plot-wrap');
    const chart = host.querySelector('.calendar-plot');
    const layer = host.querySelector('.calendar-hit-layer');
    const status = host.querySelector('.calendar-status');
    status.textContent = '';
    let disposed = false, dragging = false, updating = false, observer;
    const items = new Map(data.items.map(item => [item.id, item]));

    function targets() {
        if (disposed || dragging || !chart._fullLayout) return;
        layer.replaceChildren();
        const xa = chart._fullLayout.xaxis, ya = chart._fullLayout.yaxis;
        const rowHeight = Math.abs(ya.l2p(1) - ya.l2p(0));
        const leftBound = xa._offset, rightBound = leftBound + xa._length;
        const topBound = ya._offset, bottomBound = topBound + ya._length;
        chart.data.forEach((trace, traceIndex) => {
            (trace.customdata || []).forEach((custom, pointIndex) => {
                const b = items.get(String(custom[0]));
                if (!b) return;
                const left = Math.max(leftBound, xa._offset + xa.d2p(b.start));
                const right = Math.min(rightBound, xa._offset + xa.d2p(b.end));
                const centre = ya._offset + ya.d2p(data.rooms[b.room]);
                if (right <= left || centre < topBound || centre > bottomBound) return;
                const hit = document.createElement('div');
                hit.dataset.booking = b.id;
                hit.setAttribute('aria-label', `Booking ${b.label}, ${data.rooms[b.room]}${b.locked ? ', låst' : ''}`);
                hit.setAttribute('role', 'button'); hit.tabIndex = b.locked ? -1 : 0;
                Object.assign(hit.style, {left:`${left}px`, top:`${centre-rowHeight*.4}px`,
                    width:`${right-left}px`, height:`${rowHeight*.8}px`,
                    cursor:b.locked?'not-allowed':'grab'});
                layer.append(hit);
                let origin = 0, previousRoom = b.room;
                const reset = () => {
                    dragging = false;
                    hit.style.transform = '';
                    hit.style.background = '';
                    hit.style.opacity = '1';
                    hit.textContent = '';
                };
                const hover = () => Plotly.Fx.hover(chart, [{curveNumber:traceIndex, pointNumber:pointIndex}]);
                hit.onpointermove = e => {
                    if (dragging) hit.style.transform = `translateY(${e.clientY-origin}px)`;
                    else hover();
                };
                hit.onpointerleave = () => {if (!dragging) Plotly.Fx.unhover(chart);};
                hit.onpointerdown = e => {
                    e.stopPropagation();
                    if (e.button !== 0 || b.locked || dragging) return;
                    e.preventDefault();
                    previousRoom = b.room; origin = e.clientY; dragging = true;
                    Plotly.Fx.unhover(chart);
                    hit.setPointerCapture(e.pointerId);
                    hit.style.background = b.color;
                    hit.style.opacity = '.85';
                    hit.textContent = b.label;
                    status.textContent = 'Flyt til et andet værelse – datoerne er faste.';
                };
                hit.onpointercancel = () => {reset(); targets();};
                hit.onlostpointercapture = () => {if (dragging) {reset(); targets();}};
                function move(room) {
                    const occupied = data.items.some(other => other.id !== b.id && other.room === room
                        && Date.parse(other.start) < Date.parse(b.end)
                        && Date.parse(other.end) > Date.parse(b.start));
                    if (occupied) {
                        reset();
                        status.textContent = 'Værelset er optaget. Bookingen bliver på sin tidligere plads.';
                        setTriggerValue('move', {id:b.id, room});
                        return;
                    }
                    b.room = room;
                    const y = Array.from(chart.data[traceIndex].y);
                    y[pointIndex] = data.rooms[room];
                    dragging = false;
                    hit.style.transform = `translateY(${ya.d2p(data.rooms[room])-ya.d2p(data.rooms[previousRoom])}px)`;
                    // Move the actual Plotly bar before Python accepts the draft.
                    updating = true;
                    const range = Array.from(chart._fullLayout.xaxis.range);
                    Plotly.update(chart, {y:[y]}, {
                        'xaxis.type':'date', 'xaxis.range':range, 'xaxis.autorange':false,
                        'yaxis.type':'category', 'yaxis.range':data.figure.layout.yaxis.range,
                        'yaxis.fixedrange':true,
                    }, [traceIndex]).then(() => {
                        updating = false;
                        if (disposed) return;
                        reset(); targets();
                        status.textContent = 'Flytning i kladde – ikke gemt.';
                        setTriggerValue('move', {id:b.id, room});
                    }).catch(() => {
                        updating = false;
                        b.room = previousRoom; reset(); targets();
                        status.textContent = 'Flytningen kunne ikke vises. Prøv igen.';
                    });
                }
                hit.onpointerup = e => {
                    e.stopPropagation();
                    if (!dragging) return;
                    const rect = chart.getBoundingClientRect();
                    const x = e.clientX - rect.left, y = e.clientY - rect.top;
                    const index = Math.round(ya.p2l(y - ya._offset));
                    const room = Number(Object.keys(data.rooms)[index]);
                    if (x < leftBound || x > rightBound || y < topBound || y > bottomBound
                            || !Number.isInteger(room) || !data.rooms[room] || room === previousRoom) {
                        reset(); targets(); return;
                    }
                    move(room);
                };
                hit.onkeydown = e => {
                    if (b.locked || dragging || !['ArrowUp','ArrowDown'].includes(e.key)) return;
                    e.preventDefault(); e.stopPropagation();
                    const room = b.room + (e.key === 'ArrowUp' ? -1 : 1);
                    if (data.rooms[room]) {previousRoom = b.room; move(room);}
                };
            });
        });
    }

    Plotly.newPlot(chart, data.figure.data, data.figure.layout, {
        responsive:true, displaylogo:false, scrollZoom:true,
        modeBarButtonsToRemove:['resetScale2d'],
        modeBarButtonsToAdd:[{
            name:'Nulstil zoom', icon:Plotly.Icons.autoscale,
            click:graph => Plotly.relayout(graph, {
                'xaxis.range':data.default_range, 'xaxis.autorange':false,
            }),
        }],
    }).then(() => {
        if (disposed) {Plotly.purge(chart); return;}
        targets();
        chart.on('plotly_afterplot', targets);
        chart.on('plotly_relayout', event => {
            targets();
            if (!updating && Object.keys(event).some(key => key.startsWith('xaxis.range') || key === 'xaxis.autorange')) {
                const range = Array.from(chart._fullLayout.xaxis.range);
                setStateValue('viewport', {view_key:data.view_key, range});
            }
        });
        observer = new ResizeObserver(() => {if (!disposed) Plotly.Plots.resize(chart);});
        observer.observe(host);
    }).catch(() => {if (!disposed) status.textContent = 'Kalenderen kunne ikke vises. Genindlæs siden.';});
    return () => {
        disposed = true;
        observer?.disconnect();
        layer.replaceChildren();
        Plotly.purge(chart);
    };
}
