// Pure phrase helpers; IDs share Progress's existing extensible record map.
(function(root){
  'use strict';
  function tokens(p){return p.english.match(/[A-Za-z']+[?.!]?/g)||[];}
  function accepts(p,position,index){return Number.isInteger(position) && position>=0 && position===index && position<tokens(p).length;}
  function round(list,rand){return list.map(function(p){return {p:p,r:rand()};}).sort(function(a,b){return a.r-b.r;}).map(function(x){return x.p;});}
  // Never two choices with one picture: a child could not tell them apart.
  function choices(answer,all,rand){
    var pics={};pics[answer.image]=true;
    var others=round(all.filter(function(p){return p.id!==answer.id;}),rand).filter(function(p){
      if(p.image&&pics[p.image])return false;pics[p.image]=true;return true;});
    return round([answer].concat(others.slice(0,3)),rand);
  }
  // Ordering a one-word phrase is not a task, so the order game skips them;
  // the board has room for four word cards.
  function orderable(list){return list.filter(function(p){var n=tokens(p).length;return n>1&&n<=4;});}
  // Review: due phrases first (Progress order), then ones missed and not yet
  // relearned (box 0), then the rest.
  function reviewList(set,record,n){
    var rank=function(p){
      if(set.due.indexOf(p)>=0)return 0;
      var r=record(p.id);
      return r&&r.wrong>0&&!r.box?1:2;
    };
    return set.list.map(function(p,i){return {p:p,i:i,k:rank(p)};})
      .sort(function(a,b){return a.k-b.k||a.i-b.i;}).slice(0,n).map(function(x){return x.p;});
  }
  var lib={tokens:tokens,accepts:accepts,round:round,choices:choices,orderable:orderable,reviewList:reviewList};
  if(typeof module!=='undefined')module.exports=lib;else root.PhraseQuiz=lib;
})(this);
