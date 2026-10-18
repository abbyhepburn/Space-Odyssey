import React,{useState} from 'react';

// Keep the original sidebar appearance. Paging lets remotes reach every item
// without changing the single-page game tutorial.
export default function InformationCatalog({items,onClose}){
 const [page,setPage]=useState(0),[selected,setSelected]=useState(null),[fact,setFact]=useState(0);
 const facts=selected?[selected.fact,...(selected.details||[])]:[];
 const pages=selected?facts.length:Math.ceil(items.length/4),current=selected?fact:page;
 const turn=next=>selected?setFact(next):setPage(next);
 return <aside className="catalog-panel information-panel">
  <div className="catalog-head"><strong>{selected?.name||'SPACE INFORMATION'}</strong><button className="close" onClick={onClose} aria-label="Close information">×</button></div>
  {selected?<div className="information-fact"><small>{selected.category} · {selected.location}</small><p>{facts[fact]}</p><a href={selected.url} target="_blank" rel="noreferrer">Read source ↗</a><button onClick={()=>setSelected(null)}>← All information</button></div>:<><p>Select a space object to learn more.</p><div className="catalog-items">{items.slice(page*4,page*4+4).map(item=><button key={item.id} onClick={()=>{setSelected(item);setFact(0)}}><span>{item.name}</span><small>{item.category}</small></button>)}</div></>}
  <div className="information-pages"><button disabled={current===0} onClick={()=>turn(current-1)}>← Previous</button><span>{current+1} / {pages}</span><button disabled={current>=pages-1} onClick={()=>turn(current+1)}>Next →</button></div>
 </aside>;
}
