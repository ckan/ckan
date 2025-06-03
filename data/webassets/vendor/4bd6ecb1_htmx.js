var htmx=(function(){'use strict'
const htmx={onLoad:null,process:null,on:null,off:null,trigger:null,ajax:null,find:null,findAll:null,closest:null,values:function(elt,type){const inputValues=getInputValues(elt,type||'post')
return inputValues.values},remove:null,addClass:null,removeClass:null,toggleClass:null,takeClass:null,swap:null,defineExtension:null,removeExtension:null,logAll:null,logNone:null,logger:null,config:{historyEnabled:true,historyCacheSize:10,refreshOnHistoryMiss:false,defaultSwapStyle:'innerHTML',defaultSwapDelay:0,defaultSettleDelay:20,includeIndicatorStyles:true,indicatorClass:'htmx-indicator',requestClass:'htmx-request',addedClass:'htmx-added',settlingClass:'htmx-settling',swappingClass:'htmx-swapping',allowEval:true,allowScriptTags:true,inlineScriptNonce:'',inlineStyleNonce:'',attributesToSettle:['class','style','width','height'],withCredentials:false,timeout:0,wsReconnectDelay:'full-jitter',wsBinaryType:'blob',disableSelector:'[hx-disable], [data-hx-disable]',scrollBehavior:'instant',defaultFocusScroll:false,getCacheBusterParam:false,globalViewTransitions:false,methodsThatUseUrlParams:['get','delete'],selfRequestsOnly:true,ignoreTitle:false,scrollIntoViewOnBoost:true,triggerSpecsCache:null,disableInheritance:false,responseHandling:[{code:'204',swap:false},{code:'[23]..',swap:true},{code:'[45]..',swap:false,error:true}],allowNestedOobSwaps:true},parseInterval:null,_:null,version:'2.0.4'}
htmx.onLoad=onLoadHelper
htmx.process=processNode
htmx.on=addEventListenerImpl
htmx.off=removeEventListenerImpl
htmx.trigger=triggerEvent
htmx.ajax=ajaxHelper
htmx.find=find
htmx.findAll=findAll
htmx.closest=closest
htmx.remove=removeElement
htmx.addClass=addClassToElement
htmx.removeClass=removeClassFromElement
htmx.toggleClass=toggleClassOnElement
htmx.takeClass=takeClassForElement
htmx.swap=swap
htmx.defineExtension=defineExtension
htmx.removeExtension=removeExtension
htmx.logAll=logAll
htmx.logNone=logNone
htmx.parseInterval=parseInterval
htmx._=internalEval
const internalAPI={addTriggerHandler,bodyContains,canAccessLocalStorage,findThisElement,filterValues,swap,hasAttribute,getAttributeValue,getClosestAttributeValue,getClosestMatch,getExpressionVars,getHeaders,getInputValues,getInternalData,getSwapSpecification,getTriggerSpecs,getTarget,makeFragment,mergeObjects,makeSettleInfo,oobSwap,querySelectorExt,settleImmediately,shouldCancel,triggerEvent,triggerErrorEvent,withExtensions}
const VERBS=['get','post','put','delete','patch']
const VERB_SELECTOR=VERBS.map(function(verb){return'[hx-'+verb+'], [data-hx-'+verb+']'}).join(', ')
function parseInterval(str){if(str==undefined){return undefined}
let interval=NaN
if(str.slice(-2)=='ms'){interval=parseFloat(str.slice(0,-2))}else if(str.slice(-1)=='s'){interval=parseFloat(str.slice(0,-1))*1000}else if(str.slice(-1)=='m'){interval=parseFloat(str.slice(0,-1))*1000*60}else{interval=parseFloat(str)}
return isNaN(interval)?undefined:interval}
function getRawAttribute(elt,name){return elt instanceof Element&&elt.getAttribute(name)}
function hasAttribute(elt,qualifiedName){return!!elt.hasAttribute&&(elt.hasAttribute(qualifiedName)||elt.hasAttribute('data-'+qualifiedName))}
function getAttributeValue(elt,qualifiedName){return getRawAttribute(elt,qualifiedName)||getRawAttribute(elt,'data-'+qualifiedName)}
function parentElt(elt){const parent=elt.parentElement
if(!parent&&elt.parentNode instanceof ShadowRoot)return elt.parentNode
return parent}
function getDocument(){return document}
function getRootNode(elt,global){return elt.getRootNode?elt.getRootNode({composed:global}):getDocument()}
function getClosestMatch(elt,condition){while(elt&&!condition(elt)){elt=parentElt(elt)}
return elt||null}
function getAttributeValueWithDisinheritance(initialElement,ancestor,attributeName){const attributeValue=getAttributeValue(ancestor,attributeName)
const disinherit=getAttributeValue(ancestor,'hx-disinherit')
var inherit=getAttributeValue(ancestor,'hx-inherit')
if(initialElement!==ancestor){if(htmx.config.disableInheritance){if(inherit&&(inherit==='*'||inherit.split(' ').indexOf(attributeName)>=0)){return attributeValue}else{return null}}
if(disinherit&&(disinherit==='*'||disinherit.split(' ').indexOf(attributeName)>=0)){return'unset'}}
return attributeValue}
function getClosestAttributeValue(elt,attributeName){let closestAttr=null
getClosestMatch(elt,function(e){return!!(closestAttr=getAttributeValueWithDisinheritance(elt,asElement(e),attributeName))})
if(closestAttr!=='unset'){return closestAttr}}
function matches(elt,selector){const matchesFunction=elt instanceof Element&&(elt.matches||elt.matchesSelector||elt.msMatchesSelector||elt.mozMatchesSelector||elt.webkitMatchesSelector||elt.oMatchesSelector)
return!!matchesFunction&&matchesFunction.call(elt,selector)}
function getStartTag(str){const tagMatcher=/<([a-z][^\/\0>\x20\t\r\n\f]*)/i
const match=tagMatcher.exec(str)
if(match){return match[1].toLowerCase()}else{return''}}
function parseHTML(resp){const parser=new DOMParser()
return parser.parseFromString(resp,'text/html')}
function takeChildrenFor(fragment,elt){while(elt.childNodes.length>0){fragment.append(elt.childNodes[0])}}
function duplicateScript(script){const newScript=getDocument().createElement('script')
forEach(script.attributes,function(attr){newScript.setAttribute(attr.name,attr.value)})
newScript.textContent=script.textContent
newScript.async=false
if(htmx.config.inlineScriptNonce){newScript.nonce=htmx.config.inlineScriptNonce}
return newScript}
function isJavaScriptScriptNode(script){return script.matches('script')&&(script.type==='text/javascript'||script.type==='module'||script.type==='')}
function normalizeScriptTags(fragment){Array.from(fragment.querySelectorAll('script')).forEach((script)=>{if(isJavaScriptScriptNode(script)){const newScript=duplicateScript(script)
const parent=script.parentNode
try{parent.insertBefore(newScript,script)}catch(e){logError(e)}finally{script.remove()}}})}
function makeFragment(response){const responseWithNoHead=response.replace(/<head(\s[^>]*)?>[\s\S]*?<\/head>/i,'')
const startTag=getStartTag(responseWithNoHead)
let fragment
if(startTag==='html'){fragment=(new DocumentFragment())
const doc=parseHTML(response)
takeChildrenFor(fragment,doc.body)
fragment.title=doc.title}else if(startTag==='body'){fragment=(new DocumentFragment())
const doc=parseHTML(responseWithNoHead)
takeChildrenFor(fragment,doc.body)
fragment.title=doc.title}else{const doc=parseHTML('<body><template class="internal-htmx-wrapper">'+responseWithNoHead+'</template></body>')
fragment=(doc.querySelector('template').content)
fragment.title=doc.title
var titleElement=fragment.querySelector('title')
if(titleElement&&titleElement.parentNode===fragment){titleElement.remove()
fragment.title=titleElement.innerText}}
if(fragment){if(htmx.config.allowScriptTags){normalizeScriptTags(fragment)}else{fragment.querySelectorAll('script').forEach((script)=>script.remove())}}
return fragment}
function maybeCall(func){if(func){func()}}
function isType(o,type){return Object.prototype.toString.call(o)==='[object '+type+']'}
function isFunction(o){return typeof o==='function'}
function isRawObject(o){return isType(o,'Object')}
function getInternalData(elt){const dataProp='htmx-internal-data'
let data=elt[dataProp]
if(!data){data=elt[dataProp]={}}
return data}
function toArray(arr){const returnArr=[]
if(arr){for(let i=0;i<arr.length;i++){returnArr.push(arr[i])}}
return returnArr}
function forEach(arr,func){if(arr){for(let i=0;i<arr.length;i++){func(arr[i])}}}
function isScrolledIntoView(el){const rect=el.getBoundingClientRect()
const elemTop=rect.top
const elemBottom=rect.bottom
return elemTop<window.innerHeight&&elemBottom>=0}
function bodyContains(elt){return elt.getRootNode({composed:true})===document}
function splitOnWhitespace(trigger){return trigger.trim().split(/\s+/)}
function mergeObjects(obj1,obj2){for(const key in obj2){if(obj2.hasOwnProperty(key)){obj1[key]=obj2[key]}}
return obj1}
function parseJSON(jString){try{return JSON.parse(jString)}catch(error){logError(error)
return null}}
function canAccessLocalStorage(){const test='htmx:localStorageTest'
try{localStorage.setItem(test,test)
localStorage.removeItem(test)
return true}catch(e){return false}}
function normalizePath(path){try{const url=new URL(path)
if(url){path=url.pathname+url.search}
if(!(/^\/$/.test(path))){path=path.replace(/\/+$/,'')}
return path}catch(e){return path}}
function internalEval(str){return maybeEval(getDocument().body,function(){return eval(str)})}
function onLoadHelper(callback){const value=htmx.on('htmx:load',function(evt){callback(evt.detail.elt)})
return value}
function logAll(){htmx.logger=function(elt,event,data){if(console){console.log(event,elt,data)}}}
function logNone(){htmx.logger=null}
function find(eltOrSelector,selector){if(typeof eltOrSelector!=='string'){return eltOrSelector.querySelector(selector)}else{return find(getDocument(),eltOrSelector)}}
function findAll(eltOrSelector,selector){if(typeof eltOrSelector!=='string'){return eltOrSelector.querySelectorAll(selector)}else{return findAll(getDocument(),eltOrSelector)}}
function getWindow(){return window}
function removeElement(elt,delay){elt=resolveTarget(elt)
if(delay){getWindow().setTimeout(function(){removeElement(elt)
elt=null},delay)}else{parentElt(elt).removeChild(elt)}}
function asElement(elt){return elt instanceof Element?elt:null}
function asHtmlElement(elt){return elt instanceof HTMLElement?elt:null}
function asString(value){return typeof value==='string'?value:null}
function asParentNode(elt){return elt instanceof Element||elt instanceof Document||elt instanceof DocumentFragment?elt:null}
function addClassToElement(elt,clazz,delay){elt=asElement(resolveTarget(elt))
if(!elt){return}
if(delay){getWindow().setTimeout(function(){addClassToElement(elt,clazz)
elt=null},delay)}else{elt.classList&&elt.classList.add(clazz)}}
function removeClassFromElement(node,clazz,delay){let elt=asElement(resolveTarget(node))
if(!elt){return}
if(delay){getWindow().setTimeout(function(){removeClassFromElement(elt,clazz)
elt=null},delay)}else{if(elt.classList){elt.classList.remove(clazz)
if(elt.classList.length===0){elt.removeAttribute('class')}}}}
function toggleClassOnElement(elt,clazz){elt=resolveTarget(elt)
elt.classList.toggle(clazz)}
function takeClassForElement(elt,clazz){elt=resolveTarget(elt)
forEach(elt.parentElement.children,function(child){removeClassFromElement(child,clazz)})
addClassToElement(asElement(elt),clazz)}
function closest(elt,selector){elt=asElement(resolveTarget(elt))
if(elt&&elt.closest){return elt.closest(selector)}else{do{if(elt==null||matches(elt,selector)){return elt}}
while(elt=elt&&asElement(parentElt(elt)))
return null}}
function startsWith(str,prefix){return str.substring(0,prefix.length)===prefix}
function endsWith(str,suffix){return str.substring(str.length-suffix.length)===suffix}
function normalizeSelector(selector){const trimmedSelector=selector.trim()
if(startsWith(trimmedSelector,'<')&&endsWith(trimmedSelector,'/>')){return trimmedSelector.substring(1,trimmedSelector.length-2)}else{return trimmedSelector}}
function querySelectorAllExt(elt,selector,global){if(selector.indexOf('global ')===0){return querySelectorAllExt(elt,selector.slice(7),true)}
elt=resolveTarget(elt)
const parts=[]
{let chevronsCount=0
let offset=0
for(let i=0;i<selector.length;i++){const char=selector[i]
if(char===','&&chevronsCount===0){parts.push(selector.substring(offset,i))
offset=i+1
continue}
if(char==='<'){chevronsCount++}else if(char==='/'&&i<selector.length-1&&selector[i+1]==='>'){chevronsCount--}}
if(offset<selector.length){parts.push(selector.substring(offset))}}
const result=[]
const unprocessedParts=[]
while(parts.length>0){const selector=normalizeSelector(parts.shift())
let item
if(selector.indexOf('closest ')===0){item=closest(asElement(elt),normalizeSelector(selector.substr(8)))}else if(selector.indexOf('find ')===0){item=find(asParentNode(elt),normalizeSelector(selector.substr(5)))}else if(selector==='next'||selector==='nextElementSibling'){item=asElement(elt).nextElementSibling}else if(selector.indexOf('next ')===0){item=scanForwardQuery(elt,normalizeSelector(selector.substr(5)),!!global)}else if(selector==='previous'||selector==='previousElementSibling'){item=asElement(elt).previousElementSibling}else if(selector.indexOf('previous ')===0){item=scanBackwardsQuery(elt,normalizeSelector(selector.substr(9)),!!global)}else if(selector==='document'){item=document}else if(selector==='window'){item=window}else if(selector==='body'){item=document.body}else if(selector==='root'){item=getRootNode(elt,!!global)}else if(selector==='host'){item=((elt.getRootNode())).host}else{unprocessedParts.push(selector)}
if(item){result.push(item)}}
if(unprocessedParts.length>0){const standardSelector=unprocessedParts.join(',')
const rootNode=asParentNode(getRootNode(elt,!!global))
result.push(...toArray(rootNode.querySelectorAll(standardSelector)))}
return result}
var scanForwardQuery=function(start,match,global){const results=asParentNode(getRootNode(start,global)).querySelectorAll(match)
for(let i=0;i<results.length;i++){const elt=results[i]
if(elt.compareDocumentPosition(start)===Node.DOCUMENT_POSITION_PRECEDING){return elt}}}
var scanBackwardsQuery=function(start,match,global){const results=asParentNode(getRootNode(start,global)).querySelectorAll(match)
for(let i=results.length-1;i>=0;i--){const elt=results[i]
if(elt.compareDocumentPosition(start)===Node.DOCUMENT_POSITION_FOLLOWING){return elt}}}
function querySelectorExt(eltOrSelector,selector){if(typeof eltOrSelector!=='string'){return querySelectorAllExt(eltOrSelector,selector)[0]}else{return querySelectorAllExt(getDocument().body,eltOrSelector)[0]}}
function resolveTarget(eltOrSelector,context){if(typeof eltOrSelector==='string'){return find(asParentNode(context)||document,eltOrSelector)}else{return eltOrSelector}}
function processEventArgs(arg1,arg2,arg3,arg4){if(isFunction(arg2)){return{target:getDocument().body,event:asString(arg1),listener:arg2,options:arg3}}else{return{target:resolveTarget(arg1),event:asString(arg2),listener:arg3,options:arg4}}}
function addEventListenerImpl(arg1,arg2,arg3,arg4){ready(function(){const eventArgs=processEventArgs(arg1,arg2,arg3,arg4)
eventArgs.target.addEventListener(eventArgs.event,eventArgs.listener,eventArgs.options)})
const b=isFunction(arg2)
return b?arg2:arg3}
function removeEventListenerImpl(arg1,arg2,arg3){ready(function(){const eventArgs=processEventArgs(arg1,arg2,arg3)
eventArgs.target.removeEventListener(eventArgs.event,eventArgs.listener)})
return isFunction(arg2)?arg2:arg3}
const DUMMY_ELT=getDocument().createElement('output')
function findAttributeTargets(elt,attrName){const attrTarget=getClosestAttributeValue(elt,attrName)
if(attrTarget){if(attrTarget==='this'){return[findThisElement(elt,attrName)]}else{const result=querySelectorAllExt(elt,attrTarget)
if(result.length===0){logError('The selector "'+attrTarget+'" on '+attrName+' returned no matches!')
return[DUMMY_ELT]}else{return result}}}}
function findThisElement(elt,attribute){return asElement(getClosestMatch(elt,function(elt){return getAttributeValue(asElement(elt),attribute)!=null}))}
function getTarget(elt){const targetStr=getClosestAttributeValue(elt,'hx-target')
if(targetStr){if(targetStr==='this'){return findThisElement(elt,'hx-target')}else{return querySelectorExt(elt,targetStr)}}else{const data=getInternalData(elt)
if(data.boosted){return getDocument().body}else{return elt}}}
function shouldSettleAttribute(name){const attributesToSettle=htmx.config.attributesToSettle
for(let i=0;i<attributesToSettle.length;i++){if(name===attributesToSettle[i]){return true}}
return false}
function cloneAttributes(mergeTo,mergeFrom){forEach(mergeTo.attributes,function(attr){if(!mergeFrom.hasAttribute(attr.name)&&shouldSettleAttribute(attr.name)){mergeTo.removeAttribute(attr.name)}})
forEach(mergeFrom.attributes,function(attr){if(shouldSettleAttribute(attr.name)){mergeTo.setAttribute(attr.name,attr.value)}})}
function isInlineSwap(swapStyle,target){const extensions=getExtensions(target)
for(let i=0;i<extensions.length;i++){const extension=extensions[i]
try{if(extension.isInlineSwap(swapStyle)){return true}}catch(e){logError(e)}}
return swapStyle==='outerHTML'}
function oobSwap(oobValue,oobElement,settleInfo,rootNode){rootNode=rootNode||getDocument()
let selector='#'+getRawAttribute(oobElement,'id')
let swapStyle='outerHTML'
if(oobValue==='true'){}else if(oobValue.indexOf(':')>0){swapStyle=oobValue.substring(0,oobValue.indexOf(':'))
selector=oobValue.substring(oobValue.indexOf(':')+1)}else{swapStyle=oobValue}
oobElement.removeAttribute('hx-swap-oob')
oobElement.removeAttribute('data-hx-swap-oob')
const targets=querySelectorAllExt(rootNode,selector,false)
if(targets){forEach(targets,function(target){let fragment
const oobElementClone=oobElement.cloneNode(true)
fragment=getDocument().createDocumentFragment()
fragment.appendChild(oobElementClone)
if(!isInlineSwap(swapStyle,target)){fragment=asParentNode(oobElementClone)}
const beforeSwapDetails={shouldSwap:true,target,fragment}
if(!triggerEvent(target,'htmx:oobBeforeSwap',beforeSwapDetails))return
target=beforeSwapDetails.target
if(beforeSwapDetails.shouldSwap){handlePreservedElements(fragment)
swapWithStyle(swapStyle,target,target,fragment,settleInfo)
restorePreservedElements()}
forEach(settleInfo.elts,function(elt){triggerEvent(elt,'htmx:oobAfterSwap',beforeSwapDetails)})})
oobElement.parentNode.removeChild(oobElement)}else{oobElement.parentNode.removeChild(oobElement)
triggerErrorEvent(getDocument().body,'htmx:oobErrorNoTarget',{content:oobElement})}
return oobValue}
function restorePreservedElements(){const pantry=find('#--htmx-preserve-pantry--')
if(pantry){for(const preservedElt of[...pantry.children]){const existingElement=find('#'+preservedElt.id)
existingElement.parentNode.moveBefore(preservedElt,existingElement)
existingElement.remove()}
pantry.remove()}}
function handlePreservedElements(fragment){forEach(findAll(fragment,'[hx-preserve], [data-hx-preserve]'),function(preservedElt){const id=getAttributeValue(preservedElt,'id')
const existingElement=getDocument().getElementById(id)
if(existingElement!=null){if(preservedElt.moveBefore){let pantry=find('#--htmx-preserve-pantry--')
if(pantry==null){getDocument().body.insertAdjacentHTML('afterend',"<div id='--htmx-preserve-pantry--'></div>")
pantry=find('#--htmx-preserve-pantry--')}
pantry.moveBefore(existingElement,null)}else{preservedElt.parentNode.replaceChild(existingElement,preservedElt)}}})}
function handleAttributes(parentNode,fragment,settleInfo){forEach(fragment.querySelectorAll('[id]'),function(newNode){const id=getRawAttribute(newNode,'id')
if(id&&id.length>0){const normalizedId=id.replace("'","\\'")
const normalizedTag=newNode.tagName.replace(':','\\:')
const parentElt=asParentNode(parentNode)
const oldNode=parentElt&&parentElt.querySelector(normalizedTag+"[id='"+normalizedId+"']")
if(oldNode&&oldNode!==parentElt){const newAttributes=newNode.cloneNode()
cloneAttributes(newNode,oldNode)
settleInfo.tasks.push(function(){cloneAttributes(newNode,newAttributes)})}}})}
function makeAjaxLoadTask(child){return function(){removeClassFromElement(child,htmx.config.addedClass)
processNode(asElement(child))
processFocus(asParentNode(child))
triggerEvent(child,'htmx:load')}}
function processFocus(child){const autofocus='[autofocus]'
const autoFocusedElt=asHtmlElement(matches(child,autofocus)?child:child.querySelector(autofocus))
if(autoFocusedElt!=null){autoFocusedElt.focus()}}
function insertNodesBefore(parentNode,insertBefore,fragment,settleInfo){handleAttributes(parentNode,fragment,settleInfo)
while(fragment.childNodes.length>0){const child=fragment.firstChild
addClassToElement(asElement(child),htmx.config.addedClass)
parentNode.insertBefore(child,insertBefore)
if(child.nodeType!==Node.TEXT_NODE&&child.nodeType!==Node.COMMENT_NODE){settleInfo.tasks.push(makeAjaxLoadTask(child))}}}
function stringHash(string,hash){let char=0
while(char<string.length){hash=(hash<<5)-hash+string.charCodeAt(char++)|0}
return hash}
function attributeHash(elt){let hash=0
if(elt.attributes){for(let i=0;i<elt.attributes.length;i++){const attribute=elt.attributes[i]
if(attribute.value){hash=stringHash(attribute.name,hash)
hash=stringHash(attribute.value,hash)}}}
return hash}
function deInitOnHandlers(elt){const internalData=getInternalData(elt)
if(internalData.onHandlers){for(let i=0;i<internalData.onHandlers.length;i++){const handlerInfo=internalData.onHandlers[i]
removeEventListenerImpl(elt,handlerInfo.event,handlerInfo.listener)}
delete internalData.onHandlers}}
function deInitNode(element){const internalData=getInternalData(element)
if(internalData.timeout){clearTimeout(internalData.timeout)}
if(internalData.listenerInfos){forEach(internalData.listenerInfos,function(info){if(info.on){removeEventListenerImpl(info.on,info.trigger,info.listener)}})}
deInitOnHandlers(element)
forEach(Object.keys(internalData),function(key){if(key!=='firstInitCompleted')delete internalData[key]})}
function cleanUpElement(element){triggerEvent(element,'htmx:beforeCleanupElement')
deInitNode(element)
if(element.children){forEach(element.children,function(child){cleanUpElement(child)})}}
function swapOuterHTML(target,fragment,settleInfo){if(target instanceof Element&&target.tagName==='BODY'){return swapInnerHTML(target,fragment,settleInfo)}
let newElt
const eltBeforeNewContent=target.previousSibling
const parentNode=parentElt(target)
if(!parentNode){return}
insertNodesBefore(parentNode,target,fragment,settleInfo)
if(eltBeforeNewContent==null){newElt=parentNode.firstChild}else{newElt=eltBeforeNewContent.nextSibling}
settleInfo.elts=settleInfo.elts.filter(function(e){return e!==target})
while(newElt&&newElt!==target){if(newElt instanceof Element){settleInfo.elts.push(newElt)}
newElt=newElt.nextSibling}
cleanUpElement(target)
if(target instanceof Element){target.remove()}else{target.parentNode.removeChild(target)}}
function swapAfterBegin(target,fragment,settleInfo){return insertNodesBefore(target,target.firstChild,fragment,settleInfo)}
function swapBeforeBegin(target,fragment,settleInfo){return insertNodesBefore(parentElt(target),target,fragment,settleInfo)}
function swapBeforeEnd(target,fragment,settleInfo){return insertNodesBefore(target,null,fragment,settleInfo)}
function swapAfterEnd(target,fragment,settleInfo){return insertNodesBefore(parentElt(target),target.nextSibling,fragment,settleInfo)}
function swapDelete(target){cleanUpElement(target)
const parent=parentElt(target)
if(parent){return parent.removeChild(target)}}
function swapInnerHTML(target,fragment,settleInfo){const firstChild=target.firstChild
insertNodesBefore(target,firstChild,fragment,settleInfo)
if(firstChild){while(firstChild.nextSibling){cleanUpElement(firstChild.nextSibling)
target.removeChild(firstChild.nextSibling)}
cleanUpElement(firstChild)
target.removeChild(firstChild)}}
function swapWithStyle(swapStyle,elt,target,fragment,settleInfo){switch(swapStyle){case'none':return
case'outerHTML':swapOuterHTML(target,fragment,settleInfo)
return
case'afterbegin':swapAfterBegin(target,fragment,settleInfo)
return
case'beforebegin':swapBeforeBegin(target,fragment,settleInfo)
return
case'beforeend':swapBeforeEnd(target,fragment,settleInfo)
return
case'afterend':swapAfterEnd(target,fragment,settleInfo)
return
case'delete':swapDelete(target)
return
default:var extensions=getExtensions(elt)
for(let i=0;i<extensions.length;i++){const ext=extensions[i]
try{const newElements=ext.handleSwap(swapStyle,target,fragment,settleInfo)
if(newElements){if(Array.isArray(newElements)){for(let j=0;j<newElements.length;j++){const child=newElements[j]
if(child.nodeType!==Node.TEXT_NODE&&child.nodeType!==Node.COMMENT_NODE){settleInfo.tasks.push(makeAjaxLoadTask(child))}}}
return}}catch(e){logError(e)}}
if(swapStyle==='innerHTML'){swapInnerHTML(target,fragment,settleInfo)}else{swapWithStyle(htmx.config.defaultSwapStyle,elt,target,fragment,settleInfo)}}}
function findAndSwapOobElements(fragment,settleInfo,rootNode){var oobElts=findAll(fragment,'[hx-swap-oob], [data-hx-swap-oob]')
forEach(oobElts,function(oobElement){if(htmx.config.allowNestedOobSwaps||oobElement.parentElement===null){const oobValue=getAttributeValue(oobElement,'hx-swap-oob')
if(oobValue!=null){oobSwap(oobValue,oobElement,settleInfo,rootNode)}}else{oobElement.removeAttribute('hx-swap-oob')
oobElement.removeAttribute('data-hx-swap-oob')}})
return oobElts.length>0}
function swap(target,content,swapSpec,swapOptions){if(!swapOptions){swapOptions={}}
target=resolveTarget(target)
const rootNode=swapOptions.contextElement?getRootNode(swapOptions.contextElement,false):getDocument()
const activeElt=document.activeElement
let selectionInfo={}
try{selectionInfo={elt:activeElt,start:activeElt?activeElt.selectionStart:null,end:activeElt?activeElt.selectionEnd:null}}catch(e){}
const settleInfo=makeSettleInfo(target)
if(swapSpec.swapStyle==='textContent'){target.textContent=content}else{let fragment=makeFragment(content)
settleInfo.title=fragment.title
if(swapOptions.selectOOB){const oobSelectValues=swapOptions.selectOOB.split(',')
for(let i=0;i<oobSelectValues.length;i++){const oobSelectValue=oobSelectValues[i].split(':',2)
let id=oobSelectValue[0].trim()
if(id.indexOf('#')===0){id=id.substring(1)}
const oobValue=oobSelectValue[1]||'true'
const oobElement=fragment.querySelector('#'+id)
if(oobElement){oobSwap(oobValue,oobElement,settleInfo,rootNode)}}}
findAndSwapOobElements(fragment,settleInfo,rootNode)
forEach(findAll(fragment,'template'),function(template){if(template.content&&findAndSwapOobElements(template.content,settleInfo,rootNode)){template.remove()}})
if(swapOptions.select){const newFragment=getDocument().createDocumentFragment()
forEach(fragment.querySelectorAll(swapOptions.select),function(node){newFragment.appendChild(node)})
fragment=newFragment}
handlePreservedElements(fragment)
swapWithStyle(swapSpec.swapStyle,swapOptions.contextElement,target,fragment,settleInfo)
restorePreservedElements()}
if(selectionInfo.elt&&!bodyContains(selectionInfo.elt)&&getRawAttribute(selectionInfo.elt,'id')){const newActiveElt=document.getElementById(getRawAttribute(selectionInfo.elt,'id'))
const focusOptions={preventScroll:swapSpec.focusScroll!==undefined?!swapSpec.focusScroll:!htmx.config.defaultFocusScroll}
if(newActiveElt){if(selectionInfo.start&&newActiveElt.setSelectionRange){try{newActiveElt.setSelectionRange(selectionInfo.start,selectionInfo.end)}catch(e){}}
newActiveElt.focus(focusOptions)}}
target.classList.remove(htmx.config.swappingClass)
forEach(settleInfo.elts,function(elt){if(elt.classList){elt.classList.add(htmx.config.settlingClass)}
triggerEvent(elt,'htmx:afterSwap',swapOptions.eventInfo)})
if(swapOptions.afterSwapCallback){swapOptions.afterSwapCallback()}
if(!swapSpec.ignoreTitle){handleTitle(settleInfo.title)}
const doSettle=function(){forEach(settleInfo.tasks,function(task){task.call()})
forEach(settleInfo.elts,function(elt){if(elt.classList){elt.classList.remove(htmx.config.settlingClass)}
triggerEvent(elt,'htmx:afterSettle',swapOptions.eventInfo)})
if(swapOptions.anchor){const anchorTarget=asElement(resolveTarget('#'+swapOptions.anchor))
if(anchorTarget){anchorTarget.scrollIntoView({block:'start',behavior:'auto'})}}
updateScrollState(settleInfo.elts,swapSpec)
if(swapOptions.afterSettleCallback){swapOptions.afterSettleCallback()}}
if(swapSpec.settleDelay>0){getWindow().setTimeout(doSettle,swapSpec.settleDelay)}else{doSettle()}}
function handleTriggerHeader(xhr,header,elt){const triggerBody=xhr.getResponseHeader(header)
if(triggerBody.indexOf('{')===0){const triggers=parseJSON(triggerBody)
for(const eventName in triggers){if(triggers.hasOwnProperty(eventName)){let detail=triggers[eventName]
if(isRawObject(detail)){elt=detail.target!==undefined?detail.target:elt}else{detail={value:detail}}
triggerEvent(elt,eventName,detail)}}}else{const eventNames=triggerBody.split(',')
for(let i=0;i<eventNames.length;i++){triggerEvent(elt,eventNames[i].trim(),[])}}}
const WHITESPACE=/\s/
const WHITESPACE_OR_COMMA=/[\s,]/
const SYMBOL_START=/[_$a-zA-Z]/
const SYMBOL_CONT=/[_$a-zA-Z0-9]/
const STRINGISH_START=['"',"'",'/']
const NOT_WHITESPACE=/[^\s]/
const COMBINED_SELECTOR_START=/[{(]/
const COMBINED_SELECTOR_END=/[})]/
function tokenizeString(str){const tokens=[]
let position=0
while(position<str.length){if(SYMBOL_START.exec(str.charAt(position))){var startPosition=position
while(SYMBOL_CONT.exec(str.charAt(position+1))){position++}
tokens.push(str.substring(startPosition,position+1))}else if(STRINGISH_START.indexOf(str.charAt(position))!==-1){const startChar=str.charAt(position)
var startPosition=position
position++
while(position<str.length&&str.charAt(position)!==startChar){if(str.charAt(position)==='\\'){position++}
position++}
tokens.push(str.substring(startPosition,position+1))}else{const symbol=str.charAt(position)
tokens.push(symbol)}
position++}
return tokens}
function isPossibleRelativeReference(token,last,paramName){return SYMBOL_START.exec(token.charAt(0))&&token!=='true'&&token!=='false'&&token!=='this'&&token!==paramName&&last!=='.'}
function maybeGenerateConditional(elt,tokens,paramName){if(tokens[0]==='['){tokens.shift()
let bracketCount=1
let conditionalSource=' return (function('+paramName+'){ return ('
let last=null
while(tokens.length>0){const token=tokens[0]
if(token===']'){bracketCount--
if(bracketCount===0){if(last===null){conditionalSource=conditionalSource+'true'}
tokens.shift()
conditionalSource+=')})'
try{const conditionFunction=maybeEval(elt,function(){return Function(conditionalSource)()},function(){return true})
conditionFunction.source=conditionalSource
return conditionFunction}catch(e){triggerErrorEvent(getDocument().body,'htmx:syntax:error',{error:e,source:conditionalSource})
return null}}}else if(token==='['){bracketCount++}
if(isPossibleRelativeReference(token,last,paramName)){conditionalSource+='(('+paramName+'.'+token+') ? ('+paramName+'.'+token+') : (window.'+token+'))'}else{conditionalSource=conditionalSource+token}
last=tokens.shift()}}}
function consumeUntil(tokens,match){let result=''
while(tokens.length>0&&!match.test(tokens[0])){result+=tokens.shift()}
return result}
function consumeCSSSelector(tokens){let result
if(tokens.length>0&&COMBINED_SELECTOR_START.test(tokens[0])){tokens.shift()
result=consumeUntil(tokens,COMBINED_SELECTOR_END).trim()
tokens.shift()}else{result=consumeUntil(tokens,WHITESPACE_OR_COMMA)}
return result}
const INPUT_SELECTOR='input, textarea, select'
function parseAndCacheTrigger(elt,explicitTrigger,cache){const triggerSpecs=[]
const tokens=tokenizeString(explicitTrigger)
do{consumeUntil(tokens,NOT_WHITESPACE)
const initialLength=tokens.length
const trigger=consumeUntil(tokens,/[,\[\s]/)
if(trigger!==''){if(trigger==='every'){const every={trigger:'every'}
consumeUntil(tokens,NOT_WHITESPACE)
every.pollInterval=parseInterval(consumeUntil(tokens,/[,\[\s]/))
consumeUntil(tokens,NOT_WHITESPACE)
var eventFilter=maybeGenerateConditional(elt,tokens,'event')
if(eventFilter){every.eventFilter=eventFilter}
triggerSpecs.push(every)}else{const triggerSpec={trigger}
var eventFilter=maybeGenerateConditional(elt,tokens,'event')
if(eventFilter){triggerSpec.eventFilter=eventFilter}
consumeUntil(tokens,NOT_WHITESPACE)
while(tokens.length>0&&tokens[0]!==','){const token=tokens.shift()
if(token==='changed'){triggerSpec.changed=true}else if(token==='once'){triggerSpec.once=true}else if(token==='consume'){triggerSpec.consume=true}else if(token==='delay'&&tokens[0]===':'){tokens.shift()
triggerSpec.delay=parseInterval(consumeUntil(tokens,WHITESPACE_OR_COMMA))}else if(token==='from'&&tokens[0]===':'){tokens.shift()
if(COMBINED_SELECTOR_START.test(tokens[0])){var from_arg=consumeCSSSelector(tokens)}else{var from_arg=consumeUntil(tokens,WHITESPACE_OR_COMMA)
if(from_arg==='closest'||from_arg==='find'||from_arg==='next'||from_arg==='previous'){tokens.shift()
const selector=consumeCSSSelector(tokens)
if(selector.length>0){from_arg+=' '+selector}}}
triggerSpec.from=from_arg}else if(token==='target'&&tokens[0]===':'){tokens.shift()
triggerSpec.target=consumeCSSSelector(tokens)}else if(token==='throttle'&&tokens[0]===':'){tokens.shift()
triggerSpec.throttle=parseInterval(consumeUntil(tokens,WHITESPACE_OR_COMMA))}else if(token==='queue'&&tokens[0]===':'){tokens.shift()
triggerSpec.queue=consumeUntil(tokens,WHITESPACE_OR_COMMA)}else if(token==='root'&&tokens[0]===':'){tokens.shift()
triggerSpec[token]=consumeCSSSelector(tokens)}else if(token==='threshold'&&tokens[0]===':'){tokens.shift()
triggerSpec[token]=consumeUntil(tokens,WHITESPACE_OR_COMMA)}else{triggerErrorEvent(elt,'htmx:syntax:error',{token:tokens.shift()})}
consumeUntil(tokens,NOT_WHITESPACE)}
triggerSpecs.push(triggerSpec)}}
if(tokens.length===initialLength){triggerErrorEvent(elt,'htmx:syntax:error',{token:tokens.shift()})}
consumeUntil(tokens,NOT_WHITESPACE)}while(tokens[0]===','&&tokens.shift())
if(cache){cache[explicitTrigger]=triggerSpecs}
return triggerSpecs}
function getTriggerSpecs(elt){const explicitTrigger=getAttributeValue(elt,'hx-trigger')
let triggerSpecs=[]
if(explicitTrigger){const cache=htmx.config.triggerSpecsCache
triggerSpecs=(cache&&cache[explicitTrigger])||parseAndCacheTrigger(elt,explicitTrigger,cache)}
if(triggerSpecs.length>0){return triggerSpecs}else if(matches(elt,'form')){return[{trigger:'submit'}]}else if(matches(elt,'input[type="button"], input[type="submit"]')){return[{trigger:'click'}]}else if(matches(elt,INPUT_SELECTOR)){return[{trigger:'change'}]}else{return[{trigger:'click'}]}}
function cancelPolling(elt){getInternalData(elt).cancelled=true}
function processPolling(elt,handler,spec){const nodeData=getInternalData(elt)
nodeData.timeout=getWindow().setTimeout(function(){if(bodyContains(elt)&&nodeData.cancelled!==true){if(!maybeFilterEvent(spec,elt,makeEvent('hx:poll:trigger',{triggerSpec:spec,target:elt}))){handler(elt)}
processPolling(elt,handler,spec)}},spec.pollInterval)}
function isLocalLink(elt){return location.hostname===elt.hostname&&getRawAttribute(elt,'href')&&getRawAttribute(elt,'href').indexOf('#')!==0}
function eltIsDisabled(elt){return closest(elt,htmx.config.disableSelector)}
function boostElement(elt,nodeData,triggerSpecs){if((elt instanceof HTMLAnchorElement&&isLocalLink(elt)&&(elt.target===''||elt.target==='_self'))||(elt.tagName==='FORM'&&String(getRawAttribute(elt,'method')).toLowerCase()!=='dialog')){nodeData.boosted=true
let verb,path
if(elt.tagName==='A'){verb=(('get'))
path=getRawAttribute(elt,'href')}else{const rawAttribute=getRawAttribute(elt,'method')
verb=((rawAttribute?rawAttribute.toLowerCase():'get'))
path=getRawAttribute(elt,'action')
if(path==null||path===''){path=getDocument().location.href}
if(verb==='get'&&path.includes('?')){path=path.replace(/\?[^#]+/,'')}}
triggerSpecs.forEach(function(triggerSpec){addEventListener(elt,function(node,evt){const elt=asElement(node)
if(eltIsDisabled(elt)){cleanUpElement(elt)
return}
issueAjaxRequest(verb,path,elt,evt)},nodeData,triggerSpec,true)})}}
function shouldCancel(evt,node){const elt=asElement(node)
if(!elt){return false}
if(evt.type==='submit'||evt.type==='click'){if(elt.tagName==='FORM'){return true}
if(matches(elt,'input[type="submit"], button')&&(matches(elt,'[form]')||closest(elt,'form')!==null)){return true}
if(elt instanceof HTMLAnchorElement&&elt.href&&(elt.getAttribute('href')==='#'||elt.getAttribute('href').indexOf('#')!==0)){return true}}
return false}
function ignoreBoostedAnchorCtrlClick(elt,evt){return getInternalData(elt).boosted&&elt instanceof HTMLAnchorElement&&evt.type==='click'&&(evt.ctrlKey||evt.metaKey)}
function maybeFilterEvent(triggerSpec,elt,evt){const eventFilter=triggerSpec.eventFilter
if(eventFilter){try{return eventFilter.call(elt,evt)!==true}catch(e){const source=eventFilter.source
triggerErrorEvent(getDocument().body,'htmx:eventFilter:error',{error:e,source})
return true}}
return false}
function addEventListener(elt,handler,nodeData,triggerSpec,explicitCancel){const elementData=getInternalData(elt)
let eltsToListenOn
if(triggerSpec.from){eltsToListenOn=querySelectorAllExt(elt,triggerSpec.from)}else{eltsToListenOn=[elt]}
if(triggerSpec.changed){if(!('lastValue'in elementData)){elementData.lastValue=new WeakMap()}
eltsToListenOn.forEach(function(eltToListenOn){if(!elementData.lastValue.has(triggerSpec)){elementData.lastValue.set(triggerSpec,new WeakMap())}
elementData.lastValue.get(triggerSpec).set(eltToListenOn,eltToListenOn.value)})}
forEach(eltsToListenOn,function(eltToListenOn){const eventListener=function(evt){if(!bodyContains(elt)){eltToListenOn.removeEventListener(triggerSpec.trigger,eventListener)
return}
if(ignoreBoostedAnchorCtrlClick(elt,evt)){return}
if(explicitCancel||shouldCancel(evt,elt)){evt.preventDefault()}
if(maybeFilterEvent(triggerSpec,elt,evt)){return}
const eventData=getInternalData(evt)
eventData.triggerSpec=triggerSpec
if(eventData.handledFor==null){eventData.handledFor=[]}
if(eventData.handledFor.indexOf(elt)<0){eventData.handledFor.push(elt)
if(triggerSpec.consume){evt.stopPropagation()}
if(triggerSpec.target&&evt.target){if(!matches(asElement(evt.target),triggerSpec.target)){return}}
if(triggerSpec.once){if(elementData.triggeredOnce){return}else{elementData.triggeredOnce=true}}
if(triggerSpec.changed){const node=event.target
const value=node.value
const lastValue=elementData.lastValue.get(triggerSpec)
if(lastValue.has(node)&&lastValue.get(node)===value){return}
lastValue.set(node,value)}
if(elementData.delayed){clearTimeout(elementData.delayed)}
if(elementData.throttle){return}
if(triggerSpec.throttle>0){if(!elementData.throttle){triggerEvent(elt,'htmx:trigger')
handler(elt,evt)
elementData.throttle=getWindow().setTimeout(function(){elementData.throttle=null},triggerSpec.throttle)}}else if(triggerSpec.delay>0){elementData.delayed=getWindow().setTimeout(function(){triggerEvent(elt,'htmx:trigger')
handler(elt,evt)},triggerSpec.delay)}else{triggerEvent(elt,'htmx:trigger')
handler(elt,evt)}}}
if(nodeData.listenerInfos==null){nodeData.listenerInfos=[]}
nodeData.listenerInfos.push({trigger:triggerSpec.trigger,listener:eventListener,on:eltToListenOn})
eltToListenOn.addEventListener(triggerSpec.trigger,eventListener)})}
let windowIsScrolling=false
let scrollHandler=null
function initScrollHandler(){if(!scrollHandler){scrollHandler=function(){windowIsScrolling=true}
window.addEventListener('scroll',scrollHandler)
window.addEventListener('resize',scrollHandler)
setInterval(function(){if(windowIsScrolling){windowIsScrolling=false
forEach(getDocument().querySelectorAll("[hx-trigger*='revealed'],[data-hx-trigger*='revealed']"),function(elt){maybeReveal(elt)})}},200)}}
function maybeReveal(elt){if(!hasAttribute(elt,'data-hx-revealed')&&isScrolledIntoView(elt)){elt.setAttribute('data-hx-revealed','true')
const nodeData=getInternalData(elt)
if(nodeData.initHash){triggerEvent(elt,'revealed')}else{elt.addEventListener('htmx:afterProcessNode',function(){triggerEvent(elt,'revealed')},{once:true})}}}
function loadImmediately(elt,handler,nodeData,delay){const load=function(){if(!nodeData.loaded){nodeData.loaded=true
triggerEvent(elt,'htmx:trigger')
handler(elt)}}
if(delay>0){getWindow().setTimeout(load,delay)}else{load()}}
function processVerbs(elt,nodeData,triggerSpecs){let explicitAction=false
forEach(VERBS,function(verb){if(hasAttribute(elt,'hx-'+verb)){const path=getAttributeValue(elt,'hx-'+verb)
explicitAction=true
nodeData.path=path
nodeData.verb=verb
triggerSpecs.forEach(function(triggerSpec){addTriggerHandler(elt,triggerSpec,nodeData,function(node,evt){const elt=asElement(node)
if(closest(elt,htmx.config.disableSelector)){cleanUpElement(elt)
return}
issueAjaxRequest(verb,path,elt,evt)})})}})
return explicitAction}
function addTriggerHandler(elt,triggerSpec,nodeData,handler){if(triggerSpec.trigger==='revealed'){initScrollHandler()
addEventListener(elt,handler,nodeData,triggerSpec)
maybeReveal(asElement(elt))}else if(triggerSpec.trigger==='intersect'){const observerOptions={}
if(triggerSpec.root){observerOptions.root=querySelectorExt(elt,triggerSpec.root)}
if(triggerSpec.threshold){observerOptions.threshold=parseFloat(triggerSpec.threshold)}
const observer=new IntersectionObserver(function(entries){for(let i=0;i<entries.length;i++){const entry=entries[i]
if(entry.isIntersecting){triggerEvent(elt,'intersect')
break}}},observerOptions)
observer.observe(asElement(elt))
addEventListener(asElement(elt),handler,nodeData,triggerSpec)}else if(!nodeData.firstInitCompleted&&triggerSpec.trigger==='load'){if(!maybeFilterEvent(triggerSpec,elt,makeEvent('load',{elt}))){loadImmediately(asElement(elt),handler,nodeData,triggerSpec.delay)}}else if(triggerSpec.pollInterval>0){nodeData.polling=true
processPolling(asElement(elt),handler,triggerSpec)}else{addEventListener(elt,handler,nodeData,triggerSpec)}}
function shouldProcessHxOn(node){const elt=asElement(node)
if(!elt){return false}
const attributes=elt.attributes
for(let j=0;j<attributes.length;j++){const attrName=attributes[j].name
if(startsWith(attrName,'hx-on:')||startsWith(attrName,'data-hx-on:')||startsWith(attrName,'hx-on-')||startsWith(attrName,'data-hx-on-')){return true}}
return false}
const HX_ON_QUERY=new XPathEvaluator().createExpression('.//*[@*[ starts-with(name(), "hx-on:") or starts-with(name(), "data-hx-on:") or'+' starts-with(name(), "hx-on-") or starts-with(name(), "data-hx-on-") ]]')
function processHXOnRoot(elt,elements){if(shouldProcessHxOn(elt)){elements.push(asElement(elt))}
const iter=HX_ON_QUERY.evaluate(elt)
let node=null
while(node=iter.iterateNext())elements.push(asElement(node))}
function findHxOnWildcardElements(elt){const elements=[]
if(elt instanceof DocumentFragment){for(const child of elt.childNodes){processHXOnRoot(child,elements)}}else{processHXOnRoot(elt,elements)}
return elements}
function findElementsToProcess(elt){if(elt.querySelectorAll){const boostedSelector=', [hx-boost] a, [data-hx-boost] a, a[hx-boost], a[data-hx-boost]'
const extensionSelectors=[]
for(const e in extensions){const extension=extensions[e]
if(extension.getSelectors){var selectors=extension.getSelectors()
if(selectors){extensionSelectors.push(selectors)}}}
const results=elt.querySelectorAll(VERB_SELECTOR+boostedSelector+", form, [type='submit'],"+' [hx-ext], [data-hx-ext], [hx-trigger], [data-hx-trigger]'+extensionSelectors.flat().map(s=>', '+s).join(''))
return results}else{return[]}}
function maybeSetLastButtonClicked(evt){const elt=(closest(asElement(evt.target),"button, input[type='submit']"))
const internalData=getRelatedFormData(evt)
if(internalData){internalData.lastButtonClicked=elt}}
function maybeUnsetLastButtonClicked(evt){const internalData=getRelatedFormData(evt)
if(internalData){internalData.lastButtonClicked=null}}
function getRelatedFormData(evt){const elt=closest(asElement(evt.target),"button, input[type='submit']")
if(!elt){return}
const form=resolveTarget('#'+getRawAttribute(elt,'form'),elt.getRootNode())||closest(elt,'form')
if(!form){return}
return getInternalData(form)}
function initButtonTracking(elt){elt.addEventListener('click',maybeSetLastButtonClicked)
elt.addEventListener('focusin',maybeSetLastButtonClicked)
elt.addEventListener('focusout',maybeUnsetLastButtonClicked)}
function addHxOnEventHandler(elt,eventName,code){const nodeData=getInternalData(elt)
if(!Array.isArray(nodeData.onHandlers)){nodeData.onHandlers=[]}
let func
const listener=function(e){maybeEval(elt,function(){if(eltIsDisabled(elt)){return}
if(!func){func=new Function('event',code)}
func.call(elt,e)})}
elt.addEventListener(eventName,listener)
nodeData.onHandlers.push({event:eventName,listener})}
function processHxOnWildcard(elt){deInitOnHandlers(elt)
for(let i=0;i<elt.attributes.length;i++){const name=elt.attributes[i].name
const value=elt.attributes[i].value
if(startsWith(name,'hx-on')||startsWith(name,'data-hx-on')){const afterOnPosition=name.indexOf('-on')+3
const nextChar=name.slice(afterOnPosition,afterOnPosition+1)
if(nextChar==='-'||nextChar===':'){let eventName=name.slice(afterOnPosition+1)
if(startsWith(eventName,':')){eventName='htmx'+eventName}else if(startsWith(eventName,'-')){eventName='htmx:'+eventName.slice(1)}else if(startsWith(eventName,'htmx-')){eventName='htmx:'+eventName.slice(5)}
addHxOnEventHandler(elt,eventName,value)}}}}
function initNode(elt){if(closest(elt,htmx.config.disableSelector)){cleanUpElement(elt)
return}
const nodeData=getInternalData(elt)
const attrHash=attributeHash(elt)
if(nodeData.initHash!==attrHash){deInitNode(elt)
nodeData.initHash=attrHash
triggerEvent(elt,'htmx:beforeProcessNode')
const triggerSpecs=getTriggerSpecs(elt)
const hasExplicitHttpAction=processVerbs(elt,nodeData,triggerSpecs)
if(!hasExplicitHttpAction){if(getClosestAttributeValue(elt,'hx-boost')==='true'){boostElement(elt,nodeData,triggerSpecs)}else if(hasAttribute(elt,'hx-trigger')){triggerSpecs.forEach(function(triggerSpec){addTriggerHandler(elt,triggerSpec,nodeData,function(){})})}}
if(elt.tagName==='FORM'||(getRawAttribute(elt,'type')==='submit'&&hasAttribute(elt,'form'))){initButtonTracking(elt)}
nodeData.firstInitCompleted=true
triggerEvent(elt,'htmx:afterProcessNode')}}
function processNode(elt){elt=resolveTarget(elt)
if(closest(elt,htmx.config.disableSelector)){cleanUpElement(elt)
return}
initNode(elt)
forEach(findElementsToProcess(elt),function(child){initNode(child)})
forEach(findHxOnWildcardElements(elt),processHxOnWildcard)}
function kebabEventName(str){return str.replace(/([a-z0-9])([A-Z])/g,'$1-$2').toLowerCase()}
function makeEvent(eventName,detail){let evt
if(window.CustomEvent&&typeof window.CustomEvent==='function'){evt=new CustomEvent(eventName,{bubbles:true,cancelable:true,composed:true,detail})}else{evt=getDocument().createEvent('CustomEvent')
evt.initCustomEvent(eventName,true,true,detail)}
return evt}
function triggerErrorEvent(elt,eventName,detail){triggerEvent(elt,eventName,mergeObjects({error:eventName},detail))}
function ignoreEventForLogging(eventName){return eventName==='htmx:afterProcessNode'}
function withExtensions(elt,toDo){forEach(getExtensions(elt),function(extension){try{toDo(extension)}catch(e){logError(e)}})}
function logError(msg){if(console.error){console.error(msg)}else if(console.log){console.log('ERROR: ',msg)}}
function triggerEvent(elt,eventName,detail){elt=resolveTarget(elt)
if(detail==null){detail={}}
detail.elt=elt
const event=makeEvent(eventName,detail)
if(htmx.logger&&!ignoreEventForLogging(eventName)){htmx.logger(elt,eventName,detail)}
if(detail.error){logError(detail.error)
triggerEvent(elt,'htmx:error',{errorInfo:detail})}
let eventResult=elt.dispatchEvent(event)
const kebabName=kebabEventName(eventName)
if(eventResult&&kebabName!==eventName){const kebabedEvent=makeEvent(kebabName,event.detail)
eventResult=eventResult&&elt.dispatchEvent(kebabedEvent)}
withExtensions(asElement(elt),function(extension){eventResult=eventResult&&(extension.onEvent(eventName,event)!==false&&!event.defaultPrevented)})
return eventResult}
let currentPathForHistory=location.pathname+location.search
function getHistoryElement(){const historyElt=getDocument().querySelector('[hx-history-elt],[data-hx-history-elt]')
return historyElt||getDocument().body}
function saveToHistoryCache(url,rootElt){if(!canAccessLocalStorage()){return}
const innerHTML=cleanInnerHtmlForHistory(rootElt)
const title=getDocument().title
const scroll=window.scrollY
if(htmx.config.historyCacheSize<=0){localStorage.removeItem('htmx-history-cache')
return}
url=normalizePath(url)
const historyCache=parseJSON(localStorage.getItem('htmx-history-cache'))||[]
for(let i=0;i<historyCache.length;i++){if(historyCache[i].url===url){historyCache.splice(i,1)
break}}
const newHistoryItem={url,content:innerHTML,title,scroll}
triggerEvent(getDocument().body,'htmx:historyItemCreated',{item:newHistoryItem,cache:historyCache})
historyCache.push(newHistoryItem)
while(historyCache.length>htmx.config.historyCacheSize){historyCache.shift()}
while(historyCache.length>0){try{localStorage.setItem('htmx-history-cache',JSON.stringify(historyCache))
break}catch(e){triggerErrorEvent(getDocument().body,'htmx:historyCacheError',{cause:e,cache:historyCache})
historyCache.shift()}}}
function getCachedHistory(url){if(!canAccessLocalStorage()){return null}
url=normalizePath(url)
const historyCache=parseJSON(localStorage.getItem('htmx-history-cache'))||[]
for(let i=0;i<historyCache.length;i++){if(historyCache[i].url===url){return historyCache[i]}}
return null}
function cleanInnerHtmlForHistory(elt){const className=htmx.config.requestClass
const clone=(elt.cloneNode(true))
forEach(findAll(clone,'.'+className),function(child){removeClassFromElement(child,className)})
forEach(findAll(clone,'[data-disabled-by-htmx]'),function(child){child.removeAttribute('disabled')})
return clone.innerHTML}
function saveCurrentPageToHistory(){const elt=getHistoryElement()
const path=currentPathForHistory||location.pathname+location.search
let disableHistoryCache
try{disableHistoryCache=getDocument().querySelector('[hx-history="false" i],[data-hx-history="false" i]')}catch(e){disableHistoryCache=getDocument().querySelector('[hx-history="false"],[data-hx-history="false"]')}
if(!disableHistoryCache){triggerEvent(getDocument().body,'htmx:beforeHistorySave',{path,historyElt:elt})
saveToHistoryCache(path,elt)}
if(htmx.config.historyEnabled)history.replaceState({htmx:true},getDocument().title,window.location.href)}
function pushUrlIntoHistory(path){if(htmx.config.getCacheBusterParam){path=path.replace(/org\.htmx\.cache-buster=[^&]*&?/,'')
if(endsWith(path,'&')||endsWith(path,'?')){path=path.slice(0,-1)}}
if(htmx.config.historyEnabled){history.pushState({htmx:true},'',path)}
currentPathForHistory=path}
function replaceUrlInHistory(path){if(htmx.config.historyEnabled)history.replaceState({htmx:true},'',path)
currentPathForHistory=path}
function settleImmediately(tasks){forEach(tasks,function(task){task.call(undefined)})}
function loadHistoryFromServer(path){const request=new XMLHttpRequest()
const details={path,xhr:request}
triggerEvent(getDocument().body,'htmx:historyCacheMiss',details)
request.open('GET',path,true)
request.setRequestHeader('HX-Request','true')
request.setRequestHeader('HX-History-Restore-Request','true')
request.setRequestHeader('HX-Current-URL',getDocument().location.href)
request.onload=function(){if(this.status>=200&&this.status<400){triggerEvent(getDocument().body,'htmx:historyCacheMissLoad',details)
const fragment=makeFragment(this.response)
const content=fragment.querySelector('[hx-history-elt],[data-hx-history-elt]')||fragment
const historyElement=getHistoryElement()
const settleInfo=makeSettleInfo(historyElement)
handleTitle(fragment.title)
handlePreservedElements(fragment)
swapInnerHTML(historyElement,content,settleInfo)
restorePreservedElements()
settleImmediately(settleInfo.tasks)
currentPathForHistory=path
triggerEvent(getDocument().body,'htmx:historyRestore',{path,cacheMiss:true,serverResponse:this.response})}else{triggerErrorEvent(getDocument().body,'htmx:historyCacheMissLoadError',details)}}
request.send()}
function restoreHistory(path){saveCurrentPageToHistory()
path=path||location.pathname+location.search
const cached=getCachedHistory(path)
if(cached){const fragment=makeFragment(cached.content)
const historyElement=getHistoryElement()
const settleInfo=makeSettleInfo(historyElement)
handleTitle(cached.title)
handlePreservedElements(fragment)
swapInnerHTML(historyElement,fragment,settleInfo)
restorePreservedElements()
settleImmediately(settleInfo.tasks)
getWindow().setTimeout(function(){window.scrollTo(0,cached.scroll)},0)
currentPathForHistory=path
triggerEvent(getDocument().body,'htmx:historyRestore',{path,item:cached})}else{if(htmx.config.refreshOnHistoryMiss){window.location.reload(true)}else{loadHistoryFromServer(path)}}}
function addRequestIndicatorClasses(elt){let indicators=(findAttributeTargets(elt,'hx-indicator'))
if(indicators==null){indicators=[elt]}
forEach(indicators,function(ic){const internalData=getInternalData(ic)
internalData.requestCount=(internalData.requestCount||0)+1
ic.classList.add.call(ic.classList,htmx.config.requestClass)})
return indicators}
function disableElements(elt){let disabledElts=(findAttributeTargets(elt,'hx-disabled-elt'))
if(disabledElts==null){disabledElts=[]}
forEach(disabledElts,function(disabledElement){const internalData=getInternalData(disabledElement)
internalData.requestCount=(internalData.requestCount||0)+1
disabledElement.setAttribute('disabled','')
disabledElement.setAttribute('data-disabled-by-htmx','')})
return disabledElts}
function removeRequestIndicators(indicators,disabled){forEach(indicators.concat(disabled),function(ele){const internalData=getInternalData(ele)
internalData.requestCount=(internalData.requestCount||1)-1})
forEach(indicators,function(ic){const internalData=getInternalData(ic)
if(internalData.requestCount===0){ic.classList.remove.call(ic.classList,htmx.config.requestClass)}})
forEach(disabled,function(disabledElement){const internalData=getInternalData(disabledElement)
if(internalData.requestCount===0){disabledElement.removeAttribute('disabled')
disabledElement.removeAttribute('data-disabled-by-htmx')}})}
function haveSeenNode(processed,elt){for(let i=0;i<processed.length;i++){const node=processed[i]
if(node.isSameNode(elt)){return true}}
return false}
function shouldInclude(element){const elt=(element)
if(elt.name===''||elt.name==null||elt.disabled||closest(elt,'fieldset[disabled]')){return false}
if(elt.type==='button'||elt.type==='submit'||elt.tagName==='image'||elt.tagName==='reset'||elt.tagName==='file'){return false}
if(elt.type==='checkbox'||elt.type==='radio'){return elt.checked}
return true}
function addValueToFormData(name,value,formData){if(name!=null&&value!=null){if(Array.isArray(value)){value.forEach(function(v){formData.append(name,v)})}else{formData.append(name,value)}}}
function removeValueFromFormData(name,value,formData){if(name!=null&&value!=null){let values=formData.getAll(name)
if(Array.isArray(value)){values=values.filter(v=>value.indexOf(v)<0)}else{values=values.filter(v=>v!==value)}
formData.delete(name)
forEach(values,v=>formData.append(name,v))}}
function processInputValue(processed,formData,errors,elt,validate){if(elt==null||haveSeenNode(processed,elt)){return}else{processed.push(elt)}
if(shouldInclude(elt)){const name=getRawAttribute(elt,'name')
let value=elt.value
if(elt instanceof HTMLSelectElement&&elt.multiple){value=toArray(elt.querySelectorAll('option:checked')).map(function(e){return((e)).value})}
if(elt instanceof HTMLInputElement&&elt.files){value=toArray(elt.files)}
addValueToFormData(name,value,formData)
if(validate){validateElement(elt,errors)}}
if(elt instanceof HTMLFormElement){forEach(elt.elements,function(input){if(processed.indexOf(input)>=0){removeValueFromFormData(input.name,input.value,formData)}else{processed.push(input)}
if(validate){validateElement(input,errors)}})
new FormData(elt).forEach(function(value,name){if(value instanceof File&&value.name===''){return}
addValueToFormData(name,value,formData)})}}
function validateElement(elt,errors){const element=(elt)
if(element.willValidate){triggerEvent(element,'htmx:validation:validate')
if(!element.checkValidity()){errors.push({elt:element,message:element.validationMessage,validity:element.validity})
triggerEvent(element,'htmx:validation:failed',{message:element.validationMessage,validity:element.validity})}}}
function overrideFormData(receiver,donor){for(const key of donor.keys()){receiver.delete(key)}
donor.forEach(function(value,key){receiver.append(key,value)})
return receiver}
function getInputValues(elt,verb){const processed=[]
const formData=new FormData()
const priorityFormData=new FormData()
const errors=[]
const internalData=getInternalData(elt)
if(internalData.lastButtonClicked&&!bodyContains(internalData.lastButtonClicked)){internalData.lastButtonClicked=null}
let validate=(elt instanceof HTMLFormElement&&elt.noValidate!==true)||getAttributeValue(elt,'hx-validate')==='true'
if(internalData.lastButtonClicked){validate=validate&&internalData.lastButtonClicked.formNoValidate!==true}
if(verb!=='get'){processInputValue(processed,priorityFormData,errors,closest(elt,'form'),validate)}
processInputValue(processed,formData,errors,elt,validate)
if(internalData.lastButtonClicked||elt.tagName==='BUTTON'||(elt.tagName==='INPUT'&&getRawAttribute(elt,'type')==='submit')){const button=internalData.lastButtonClicked||((elt))
const name=getRawAttribute(button,'name')
addValueToFormData(name,button.value,priorityFormData)}
const includes=findAttributeTargets(elt,'hx-include')
forEach(includes,function(node){processInputValue(processed,formData,errors,asElement(node),validate)
if(!matches(node,'form')){forEach(asParentNode(node).querySelectorAll(INPUT_SELECTOR),function(descendant){processInputValue(processed,formData,errors,descendant,validate)})}})
overrideFormData(formData,priorityFormData)
return{errors,formData,values:formDataProxy(formData)}}
function appendParam(returnStr,name,realValue){if(returnStr!==''){returnStr+='&'}
if(String(realValue)==='[object Object]'){realValue=JSON.stringify(realValue)}
const s=encodeURIComponent(realValue)
returnStr+=encodeURIComponent(name)+'='+s
return returnStr}
function urlEncode(values){values=formDataFromObject(values)
let returnStr=''
values.forEach(function(value,key){returnStr=appendParam(returnStr,key,value)})
return returnStr}
function getHeaders(elt,target,prompt){const headers={'HX-Request':'true','HX-Trigger':getRawAttribute(elt,'id'),'HX-Trigger-Name':getRawAttribute(elt,'name'),'HX-Target':getAttributeValue(target,'id'),'HX-Current-URL':getDocument().location.href}
getValuesForElement(elt,'hx-headers',false,headers)
if(prompt!==undefined){headers['HX-Prompt']=prompt}
if(getInternalData(elt).boosted){headers['HX-Boosted']='true'}
return headers}
function filterValues(inputValues,elt){const paramsValue=getClosestAttributeValue(elt,'hx-params')
if(paramsValue){if(paramsValue==='none'){return new FormData()}else if(paramsValue==='*'){return inputValues}else if(paramsValue.indexOf('not ')===0){forEach(paramsValue.slice(4).split(','),function(name){name=name.trim()
inputValues.delete(name)})
return inputValues}else{const newValues=new FormData()
forEach(paramsValue.split(','),function(name){name=name.trim()
if(inputValues.has(name)){inputValues.getAll(name).forEach(function(value){newValues.append(name,value)})}})
return newValues}}else{return inputValues}}
function isAnchorLink(elt){return!!getRawAttribute(elt,'href')&&getRawAttribute(elt,'href').indexOf('#')>=0}
function getSwapSpecification(elt,swapInfoOverride){const swapInfo=swapInfoOverride||getClosestAttributeValue(elt,'hx-swap')
const swapSpec={swapStyle:getInternalData(elt).boosted?'innerHTML':htmx.config.defaultSwapStyle,swapDelay:htmx.config.defaultSwapDelay,settleDelay:htmx.config.defaultSettleDelay}
if(htmx.config.scrollIntoViewOnBoost&&getInternalData(elt).boosted&&!isAnchorLink(elt)){swapSpec.show='top'}
if(swapInfo){const split=splitOnWhitespace(swapInfo)
if(split.length>0){for(let i=0;i<split.length;i++){const value=split[i]
if(value.indexOf('swap:')===0){swapSpec.swapDelay=parseInterval(value.slice(5))}else if(value.indexOf('settle:')===0){swapSpec.settleDelay=parseInterval(value.slice(7))}else if(value.indexOf('transition:')===0){swapSpec.transition=value.slice(11)==='true'}else if(value.indexOf('ignoreTitle:')===0){swapSpec.ignoreTitle=value.slice(12)==='true'}else if(value.indexOf('scroll:')===0){const scrollSpec=value.slice(7)
var splitSpec=scrollSpec.split(':')
const scrollVal=splitSpec.pop()
var selectorVal=splitSpec.length>0?splitSpec.join(':'):null
swapSpec.scroll=scrollVal
swapSpec.scrollTarget=selectorVal}else if(value.indexOf('show:')===0){const showSpec=value.slice(5)
var splitSpec=showSpec.split(':')
const showVal=splitSpec.pop()
var selectorVal=splitSpec.length>0?splitSpec.join(':'):null
swapSpec.show=showVal
swapSpec.showTarget=selectorVal}else if(value.indexOf('focus-scroll:')===0){const focusScrollVal=value.slice('focus-scroll:'.length)
swapSpec.focusScroll=focusScrollVal=='true'}else if(i==0){swapSpec.swapStyle=value}else{logError('Unknown modifier in hx-swap: '+value)}}}}
return swapSpec}
function usesFormData(elt){return getClosestAttributeValue(elt,'hx-encoding')==='multipart/form-data'||(matches(elt,'form')&&getRawAttribute(elt,'enctype')==='multipart/form-data')}
function encodeParamsForBody(xhr,elt,filteredParameters){let encodedParameters=null
withExtensions(elt,function(extension){if(encodedParameters==null){encodedParameters=extension.encodeParameters(xhr,filteredParameters,elt)}})
if(encodedParameters!=null){return encodedParameters}else{if(usesFormData(elt)){return overrideFormData(new FormData(),formDataFromObject(filteredParameters))}else{return urlEncode(filteredParameters)}}}
function makeSettleInfo(target){return{tasks:[],elts:[target]}}
function updateScrollState(content,swapSpec){const first=content[0]
const last=content[content.length-1]
if(swapSpec.scroll){var target=null
if(swapSpec.scrollTarget){target=asElement(querySelectorExt(first,swapSpec.scrollTarget))}
if(swapSpec.scroll==='top'&&(first||target)){target=target||first
target.scrollTop=0}
if(swapSpec.scroll==='bottom'&&(last||target)){target=target||last
target.scrollTop=target.scrollHeight}}
if(swapSpec.show){var target=null
if(swapSpec.showTarget){let targetStr=swapSpec.showTarget
if(swapSpec.showTarget==='window'){targetStr='body'}
target=asElement(querySelectorExt(first,targetStr))}
if(swapSpec.show==='top'&&(first||target)){target=target||first
target.scrollIntoView({block:'start',behavior:htmx.config.scrollBehavior})}
if(swapSpec.show==='bottom'&&(last||target)){target=target||last
target.scrollIntoView({block:'end',behavior:htmx.config.scrollBehavior})}}}
function getValuesForElement(elt,attr,evalAsDefault,values){if(values==null){values={}}
if(elt==null){return values}
const attributeValue=getAttributeValue(elt,attr)
if(attributeValue){let str=attributeValue.trim()
let evaluateValue=evalAsDefault
if(str==='unset'){return null}
if(str.indexOf('javascript:')===0){str=str.slice(11)
evaluateValue=true}else if(str.indexOf('js:')===0){str=str.slice(3)
evaluateValue=true}
if(str.indexOf('{')!==0){str='{'+str+'}'}
let varsValues
if(evaluateValue){varsValues=maybeEval(elt,function(){return Function('return ('+str+')')()},{})}else{varsValues=parseJSON(str)}
for(const key in varsValues){if(varsValues.hasOwnProperty(key)){if(values[key]==null){values[key]=varsValues[key]}}}}
return getValuesForElement(asElement(parentElt(elt)),attr,evalAsDefault,values)}
function maybeEval(elt,toEval,defaultVal){if(htmx.config.allowEval){return toEval()}else{triggerErrorEvent(elt,'htmx:evalDisallowedError')
return defaultVal}}
function getHXVarsForElement(elt,expressionVars){return getValuesForElement(elt,'hx-vars',true,expressionVars)}
function getHXValsForElement(elt,expressionVars){return getValuesForElement(elt,'hx-vals',false,expressionVars)}
function getExpressionVars(elt){return mergeObjects(getHXVarsForElement(elt),getHXValsForElement(elt))}
function safelySetHeaderValue(xhr,header,headerValue){if(headerValue!==null){try{xhr.setRequestHeader(header,headerValue)}catch(e){xhr.setRequestHeader(header,encodeURIComponent(headerValue))
xhr.setRequestHeader(header+'-URI-AutoEncoded','true')}}}
function getPathFromResponse(xhr){if(xhr.responseURL&&typeof(URL)!=='undefined'){try{const url=new URL(xhr.responseURL)
return url.pathname+url.search}catch(e){triggerErrorEvent(getDocument().body,'htmx:badResponseUrl',{url:xhr.responseURL})}}}
function hasHeader(xhr,regexp){return regexp.test(xhr.getAllResponseHeaders())}
function ajaxHelper(verb,path,context){verb=((verb.toLowerCase()))
if(context){if(context instanceof Element||typeof context==='string'){return issueAjaxRequest(verb,path,null,null,{targetOverride:resolveTarget(context)||DUMMY_ELT,returnPromise:true})}else{let resolvedTarget=resolveTarget(context.target)
if((context.target&&!resolvedTarget)||(context.source&&!resolvedTarget&&!resolveTarget(context.source))){resolvedTarget=DUMMY_ELT}
return issueAjaxRequest(verb,path,resolveTarget(context.source),context.event,{handler:context.handler,headers:context.headers,values:context.values,targetOverride:resolvedTarget,swapOverride:context.swap,select:context.select,returnPromise:true})}}else{return issueAjaxRequest(verb,path,null,null,{returnPromise:true})}}
function hierarchyForElt(elt){const arr=[]
while(elt){arr.push(elt)
elt=elt.parentElement}
return arr}
function verifyPath(elt,path,requestConfig){let sameHost
let url
if(typeof URL==='function'){url=new URL(path,document.location.href)
const origin=document.location.origin
sameHost=origin===url.origin}else{url=path
sameHost=startsWith(path,document.location.origin)}
if(htmx.config.selfRequestsOnly){if(!sameHost){return false}}
return triggerEvent(elt,'htmx:validateUrl',mergeObjects({url,sameHost},requestConfig))}
function formDataFromObject(obj){if(obj instanceof FormData)return obj
const formData=new FormData()
for(const key in obj){if(obj.hasOwnProperty(key)){if(obj[key]&&typeof obj[key].forEach==='function'){obj[key].forEach(function(v){formData.append(key,v)})}else if(typeof obj[key]==='object'&&!(obj[key]instanceof Blob)){formData.append(key,JSON.stringify(obj[key]))}else{formData.append(key,obj[key])}}}
return formData}
function formDataArrayProxy(formData,name,array){return new Proxy(array,{get:function(target,key){if(typeof key==='number')return target[key]
if(key==='length')return target.length
if(key==='push'){return function(value){target.push(value)
formData.append(name,value)}}
if(typeof target[key]==='function'){return function(){target[key].apply(target,arguments)
formData.delete(name)
target.forEach(function(v){formData.append(name,v)})}}
if(target[key]&&target[key].length===1){return target[key][0]}else{return target[key]}},set:function(target,index,value){target[index]=value
formData.delete(name)
target.forEach(function(v){formData.append(name,v)})
return true}})}
function formDataProxy(formData){return new Proxy(formData,{get:function(target,name){if(typeof name==='symbol'){const result=Reflect.get(target,name)
if(typeof result==='function'){return function(){return result.apply(formData,arguments)}}else{return result}}
if(name==='toJSON'){return()=>Object.fromEntries(formData)}
if(name in target){if(typeof target[name]==='function'){return function(){return formData[name].apply(formData,arguments)}}else{return target[name]}}
const array=formData.getAll(name)
if(array.length===0){return undefined}else if(array.length===1){return array[0]}else{return formDataArrayProxy(target,name,array)}},set:function(target,name,value){if(typeof name!=='string'){return false}
target.delete(name)
if(value&&typeof value.forEach==='function'){value.forEach(function(v){target.append(name,v)})}else if(typeof value==='object'&&!(value instanceof Blob)){target.append(name,JSON.stringify(value))}else{target.append(name,value)}
return true},deleteProperty:function(target,name){if(typeof name==='string'){target.delete(name)}
return true},ownKeys:function(target){return Reflect.ownKeys(Object.fromEntries(target))},getOwnPropertyDescriptor:function(target,prop){return Reflect.getOwnPropertyDescriptor(Object.fromEntries(target),prop)}})}
function issueAjaxRequest(verb,path,elt,event,etc,confirmed){let resolve=null
let reject=null
etc=etc!=null?etc:{}
if(etc.returnPromise&&typeof Promise!=='undefined'){var promise=new Promise(function(_resolve,_reject){resolve=_resolve
reject=_reject})}
if(elt==null){elt=getDocument().body}
const responseHandler=etc.handler||handleAjaxResponse
const select=etc.select||null
if(!bodyContains(elt)){maybeCall(resolve)
return promise}
const target=etc.targetOverride||asElement(getTarget(elt))
if(target==null||target==DUMMY_ELT){triggerErrorEvent(elt,'htmx:targetError',{target:getAttributeValue(elt,'hx-target')})
maybeCall(reject)
return promise}
let eltData=getInternalData(elt)
const submitter=eltData.lastButtonClicked
if(submitter){const buttonPath=getRawAttribute(submitter,'formaction')
if(buttonPath!=null){path=buttonPath}
const buttonVerb=getRawAttribute(submitter,'formmethod')
if(buttonVerb!=null){if(buttonVerb.toLowerCase()!=='dialog'){verb=((buttonVerb))}}}
const confirmQuestion=getClosestAttributeValue(elt,'hx-confirm')
if(confirmed===undefined){const issueRequest=function(skipConfirmation){return issueAjaxRequest(verb,path,elt,event,etc,!!skipConfirmation)}
const confirmDetails={target,elt,path,verb,triggeringEvent:event,etc,issueRequest,question:confirmQuestion}
if(triggerEvent(elt,'htmx:confirm',confirmDetails)===false){maybeCall(resolve)
return promise}}
let syncElt=elt
let syncStrategy=getClosestAttributeValue(elt,'hx-sync')
let queueStrategy=null
let abortable=false
if(syncStrategy){const syncStrings=syncStrategy.split(':')
const selector=syncStrings[0].trim()
if(selector==='this'){syncElt=findThisElement(elt,'hx-sync')}else{syncElt=asElement(querySelectorExt(elt,selector))}
syncStrategy=(syncStrings[1]||'drop').trim()
eltData=getInternalData(syncElt)
if(syncStrategy==='drop'&&eltData.xhr&&eltData.abortable!==true){maybeCall(resolve)
return promise}else if(syncStrategy==='abort'){if(eltData.xhr){maybeCall(resolve)
return promise}else{abortable=true}}else if(syncStrategy==='replace'){triggerEvent(syncElt,'htmx:abort')}else if(syncStrategy.indexOf('queue')===0){const queueStrArray=syncStrategy.split(' ')
queueStrategy=(queueStrArray[1]||'last').trim()}}
if(eltData.xhr){if(eltData.abortable){triggerEvent(syncElt,'htmx:abort')}else{if(queueStrategy==null){if(event){const eventData=getInternalData(event)
if(eventData&&eventData.triggerSpec&&eventData.triggerSpec.queue){queueStrategy=eventData.triggerSpec.queue}}
if(queueStrategy==null){queueStrategy='last'}}
if(eltData.queuedRequests==null){eltData.queuedRequests=[]}
if(queueStrategy==='first'&&eltData.queuedRequests.length===0){eltData.queuedRequests.push(function(){issueAjaxRequest(verb,path,elt,event,etc)})}else if(queueStrategy==='all'){eltData.queuedRequests.push(function(){issueAjaxRequest(verb,path,elt,event,etc)})}else if(queueStrategy==='last'){eltData.queuedRequests=[]
eltData.queuedRequests.push(function(){issueAjaxRequest(verb,path,elt,event,etc)})}
maybeCall(resolve)
return promise}}
const xhr=new XMLHttpRequest()
eltData.xhr=xhr
eltData.abortable=abortable
const endRequestLock=function(){eltData.xhr=null
eltData.abortable=false
if(eltData.queuedRequests!=null&&eltData.queuedRequests.length>0){const queuedRequest=eltData.queuedRequests.shift()
queuedRequest()}}
const promptQuestion=getClosestAttributeValue(elt,'hx-prompt')
if(promptQuestion){var promptResponse=prompt(promptQuestion)
if(promptResponse===null||!triggerEvent(elt,'htmx:prompt',{prompt:promptResponse,target})){maybeCall(resolve)
endRequestLock()
return promise}}
if(confirmQuestion&&!confirmed){if(!confirm(confirmQuestion)){maybeCall(resolve)
endRequestLock()
return promise}}
let headers=getHeaders(elt,target,promptResponse)
if(verb!=='get'&&!usesFormData(elt)){headers['Content-Type']='application/x-www-form-urlencoded'}
if(etc.headers){headers=mergeObjects(headers,etc.headers)}
const results=getInputValues(elt,verb)
let errors=results.errors
const rawFormData=results.formData
if(etc.values){overrideFormData(rawFormData,formDataFromObject(etc.values))}
const expressionVars=formDataFromObject(getExpressionVars(elt))
const allFormData=overrideFormData(rawFormData,expressionVars)
let filteredFormData=filterValues(allFormData,elt)
if(htmx.config.getCacheBusterParam&&verb==='get'){filteredFormData.set('org.htmx.cache-buster',getRawAttribute(target,'id')||'true')}
if(path==null||path===''){path=getDocument().location.href}
const requestAttrValues=getValuesForElement(elt,'hx-request')
const eltIsBoosted=getInternalData(elt).boosted
let useUrlParams=htmx.config.methodsThatUseUrlParams.indexOf(verb)>=0
const requestConfig={boosted:eltIsBoosted,useUrlParams,formData:filteredFormData,parameters:formDataProxy(filteredFormData),unfilteredFormData:allFormData,unfilteredParameters:formDataProxy(allFormData),headers,target,verb,errors,withCredentials:etc.credentials||requestAttrValues.credentials||htmx.config.withCredentials,timeout:etc.timeout||requestAttrValues.timeout||htmx.config.timeout,path,triggeringEvent:event}
if(!triggerEvent(elt,'htmx:configRequest',requestConfig)){maybeCall(resolve)
endRequestLock()
return promise}
path=requestConfig.path
verb=requestConfig.verb
headers=requestConfig.headers
filteredFormData=formDataFromObject(requestConfig.parameters)
errors=requestConfig.errors
useUrlParams=requestConfig.useUrlParams
if(errors&&errors.length>0){triggerEvent(elt,'htmx:validation:halted',requestConfig)
maybeCall(resolve)
endRequestLock()
return promise}
const splitPath=path.split('#')
const pathNoAnchor=splitPath[0]
const anchor=splitPath[1]
let finalPath=path
if(useUrlParams){finalPath=pathNoAnchor
const hasValues=!filteredFormData.keys().next().done
if(hasValues){if(finalPath.indexOf('?')<0){finalPath+='?'}else{finalPath+='&'}
finalPath+=urlEncode(filteredFormData)
if(anchor){finalPath+='#'+anchor}}}
if(!verifyPath(elt,finalPath,requestConfig)){triggerErrorEvent(elt,'htmx:invalidPath',requestConfig)
maybeCall(reject)
return promise}
xhr.open(verb.toUpperCase(),finalPath,true)
xhr.overrideMimeType('text/html')
xhr.withCredentials=requestConfig.withCredentials
xhr.timeout=requestConfig.timeout
if(requestAttrValues.noHeaders){}else{for(const header in headers){if(headers.hasOwnProperty(header)){const headerValue=headers[header]
safelySetHeaderValue(xhr,header,headerValue)}}}
const responseInfo={xhr,target,requestConfig,etc,boosted:eltIsBoosted,select,pathInfo:{requestPath:path,finalRequestPath:finalPath,responsePath:null,anchor}}
xhr.onload=function(){try{const hierarchy=hierarchyForElt(elt)
responseInfo.pathInfo.responsePath=getPathFromResponse(xhr)
responseHandler(elt,responseInfo)
if(responseInfo.keepIndicators!==true){removeRequestIndicators(indicators,disableElts)}
triggerEvent(elt,'htmx:afterRequest',responseInfo)
triggerEvent(elt,'htmx:afterOnLoad',responseInfo)
if(!bodyContains(elt)){let secondaryTriggerElt=null
while(hierarchy.length>0&&secondaryTriggerElt==null){const parentEltInHierarchy=hierarchy.shift()
if(bodyContains(parentEltInHierarchy)){secondaryTriggerElt=parentEltInHierarchy}}
if(secondaryTriggerElt){triggerEvent(secondaryTriggerElt,'htmx:afterRequest',responseInfo)
triggerEvent(secondaryTriggerElt,'htmx:afterOnLoad',responseInfo)}}
maybeCall(resolve)
endRequestLock()}catch(e){triggerErrorEvent(elt,'htmx:onLoadError',mergeObjects({error:e},responseInfo))
throw e}}
xhr.onerror=function(){removeRequestIndicators(indicators,disableElts)
triggerErrorEvent(elt,'htmx:afterRequest',responseInfo)
triggerErrorEvent(elt,'htmx:sendError',responseInfo)
maybeCall(reject)
endRequestLock()}
xhr.onabort=function(){removeRequestIndicators(indicators,disableElts)
triggerErrorEvent(elt,'htmx:afterRequest',responseInfo)
triggerErrorEvent(elt,'htmx:sendAbort',responseInfo)
maybeCall(reject)
endRequestLock()}
xhr.ontimeout=function(){removeRequestIndicators(indicators,disableElts)
triggerErrorEvent(elt,'htmx:afterRequest',responseInfo)
triggerErrorEvent(elt,'htmx:timeout',responseInfo)
maybeCall(reject)
endRequestLock()}
if(!triggerEvent(elt,'htmx:beforeRequest',responseInfo)){maybeCall(resolve)
endRequestLock()
return promise}
var indicators=addRequestIndicatorClasses(elt)
var disableElts=disableElements(elt)
forEach(['loadstart','loadend','progress','abort'],function(eventName){forEach([xhr,xhr.upload],function(target){target.addEventListener(eventName,function(event){triggerEvent(elt,'htmx:xhr:'+eventName,{lengthComputable:event.lengthComputable,loaded:event.loaded,total:event.total})})})})
triggerEvent(elt,'htmx:beforeSend',responseInfo)
const params=useUrlParams?null:encodeParamsForBody(xhr,elt,filteredFormData)
xhr.send(params)
return promise}
function determineHistoryUpdates(elt,responseInfo){const xhr=responseInfo.xhr
let pathFromHeaders=null
let typeFromHeaders=null
if(hasHeader(xhr,/HX-Push:/i)){pathFromHeaders=xhr.getResponseHeader('HX-Push')
typeFromHeaders='push'}else if(hasHeader(xhr,/HX-Push-Url:/i)){pathFromHeaders=xhr.getResponseHeader('HX-Push-Url')
typeFromHeaders='push'}else if(hasHeader(xhr,/HX-Replace-Url:/i)){pathFromHeaders=xhr.getResponseHeader('HX-Replace-Url')
typeFromHeaders='replace'}
if(pathFromHeaders){if(pathFromHeaders==='false'){return{}}else{return{type:typeFromHeaders,path:pathFromHeaders}}}
const requestPath=responseInfo.pathInfo.finalRequestPath
const responsePath=responseInfo.pathInfo.responsePath
const pushUrl=getClosestAttributeValue(elt,'hx-push-url')
const replaceUrl=getClosestAttributeValue(elt,'hx-replace-url')
const elementIsBoosted=getInternalData(elt).boosted
let saveType=null
let path=null
if(pushUrl){saveType='push'
path=pushUrl}else if(replaceUrl){saveType='replace'
path=replaceUrl}else if(elementIsBoosted){saveType='push'
path=responsePath||requestPath}
if(path){if(path==='false'){return{}}
if(path==='true'){path=responsePath||requestPath}
if(responseInfo.pathInfo.anchor&&path.indexOf('#')===-1){path=path+'#'+responseInfo.pathInfo.anchor}
return{type:saveType,path}}else{return{}}}
function codeMatches(responseHandlingConfig,status){var regExp=new RegExp(responseHandlingConfig.code)
return regExp.test(status.toString(10))}
function resolveResponseHandling(xhr){for(var i=0;i<htmx.config.responseHandling.length;i++){var responseHandlingElement=htmx.config.responseHandling[i]
if(codeMatches(responseHandlingElement,xhr.status)){return responseHandlingElement}}
return{swap:false}}
function handleTitle(title){if(title){const titleElt=find('title')
if(titleElt){titleElt.innerHTML=title}else{window.document.title=title}}}
function handleAjaxResponse(elt,responseInfo){const xhr=responseInfo.xhr
let target=responseInfo.target
const etc=responseInfo.etc
const responseInfoSelect=responseInfo.select
if(!triggerEvent(elt,'htmx:beforeOnLoad',responseInfo))return
if(hasHeader(xhr,/HX-Trigger:/i)){handleTriggerHeader(xhr,'HX-Trigger',elt)}
if(hasHeader(xhr,/HX-Location:/i)){saveCurrentPageToHistory()
let redirectPath=xhr.getResponseHeader('HX-Location')
var redirectSwapSpec
if(redirectPath.indexOf('{')===0){redirectSwapSpec=parseJSON(redirectPath)
redirectPath=redirectSwapSpec.path
delete redirectSwapSpec.path}
ajaxHelper('get',redirectPath,redirectSwapSpec).then(function(){pushUrlIntoHistory(redirectPath)})
return}
const shouldRefresh=hasHeader(xhr,/HX-Refresh:/i)&&xhr.getResponseHeader('HX-Refresh')==='true'
if(hasHeader(xhr,/HX-Redirect:/i)){responseInfo.keepIndicators=true
location.href=xhr.getResponseHeader('HX-Redirect')
shouldRefresh&&location.reload()
return}
if(shouldRefresh){responseInfo.keepIndicators=true
location.reload()
return}
if(hasHeader(xhr,/HX-Retarget:/i)){if(xhr.getResponseHeader('HX-Retarget')==='this'){responseInfo.target=elt}else{responseInfo.target=asElement(querySelectorExt(elt,xhr.getResponseHeader('HX-Retarget')))}}
const historyUpdate=determineHistoryUpdates(elt,responseInfo)
const responseHandling=resolveResponseHandling(xhr)
const shouldSwap=responseHandling.swap
let isError=!!responseHandling.error
let ignoreTitle=htmx.config.ignoreTitle||responseHandling.ignoreTitle
let selectOverride=responseHandling.select
if(responseHandling.target){responseInfo.target=asElement(querySelectorExt(elt,responseHandling.target))}
var swapOverride=etc.swapOverride
if(swapOverride==null&&responseHandling.swapOverride){swapOverride=responseHandling.swapOverride}
if(hasHeader(xhr,/HX-Retarget:/i)){if(xhr.getResponseHeader('HX-Retarget')==='this'){responseInfo.target=elt}else{responseInfo.target=asElement(querySelectorExt(elt,xhr.getResponseHeader('HX-Retarget')))}}
if(hasHeader(xhr,/HX-Reswap:/i)){swapOverride=xhr.getResponseHeader('HX-Reswap')}
var serverResponse=xhr.response
var beforeSwapDetails=mergeObjects({shouldSwap,serverResponse,isError,ignoreTitle,selectOverride,swapOverride},responseInfo)
if(responseHandling.event&&!triggerEvent(target,responseHandling.event,beforeSwapDetails))return
if(!triggerEvent(target,'htmx:beforeSwap',beforeSwapDetails))return
target=beforeSwapDetails.target
serverResponse=beforeSwapDetails.serverResponse
isError=beforeSwapDetails.isError
ignoreTitle=beforeSwapDetails.ignoreTitle
selectOverride=beforeSwapDetails.selectOverride
swapOverride=beforeSwapDetails.swapOverride
responseInfo.target=target
responseInfo.failed=isError
responseInfo.successful=!isError
if(beforeSwapDetails.shouldSwap){if(xhr.status===286){cancelPolling(elt)}
withExtensions(elt,function(extension){serverResponse=extension.transformResponse(serverResponse,xhr,elt)})
if(historyUpdate.type){saveCurrentPageToHistory()}
var swapSpec=getSwapSpecification(elt,swapOverride)
if(!swapSpec.hasOwnProperty('ignoreTitle')){swapSpec.ignoreTitle=ignoreTitle}
target.classList.add(htmx.config.swappingClass)
let settleResolve=null
let settleReject=null
if(responseInfoSelect){selectOverride=responseInfoSelect}
if(hasHeader(xhr,/HX-Reselect:/i)){selectOverride=xhr.getResponseHeader('HX-Reselect')}
const selectOOB=getClosestAttributeValue(elt,'hx-select-oob')
const select=getClosestAttributeValue(elt,'hx-select')
let doSwap=function(){try{if(historyUpdate.type){triggerEvent(getDocument().body,'htmx:beforeHistoryUpdate',mergeObjects({history:historyUpdate},responseInfo))
if(historyUpdate.type==='push'){pushUrlIntoHistory(historyUpdate.path)
triggerEvent(getDocument().body,'htmx:pushedIntoHistory',{path:historyUpdate.path})}else{replaceUrlInHistory(historyUpdate.path)
triggerEvent(getDocument().body,'htmx:replacedInHistory',{path:historyUpdate.path})}}
swap(target,serverResponse,swapSpec,{select:selectOverride||select,selectOOB,eventInfo:responseInfo,anchor:responseInfo.pathInfo.anchor,contextElement:elt,afterSwapCallback:function(){if(hasHeader(xhr,/HX-Trigger-After-Swap:/i)){let finalElt=elt
if(!bodyContains(elt)){finalElt=getDocument().body}
handleTriggerHeader(xhr,'HX-Trigger-After-Swap',finalElt)}},afterSettleCallback:function(){if(hasHeader(xhr,/HX-Trigger-After-Settle:/i)){let finalElt=elt
if(!bodyContains(elt)){finalElt=getDocument().body}
handleTriggerHeader(xhr,'HX-Trigger-After-Settle',finalElt)}
maybeCall(settleResolve)}})}catch(e){triggerErrorEvent(elt,'htmx:swapError',responseInfo)
maybeCall(settleReject)
throw e}}
let shouldTransition=htmx.config.globalViewTransitions
if(swapSpec.hasOwnProperty('transition')){shouldTransition=swapSpec.transition}
if(shouldTransition&&triggerEvent(elt,'htmx:beforeTransition',responseInfo)&&typeof Promise!=='undefined'&&document.startViewTransition){const settlePromise=new Promise(function(_resolve,_reject){settleResolve=_resolve
settleReject=_reject})
const innerDoSwap=doSwap
doSwap=function(){document.startViewTransition(function(){innerDoSwap()
return settlePromise})}}
if(swapSpec.swapDelay>0){getWindow().setTimeout(doSwap,swapSpec.swapDelay)}else{doSwap()}}
if(isError){triggerErrorEvent(elt,'htmx:responseError',mergeObjects({error:'Response Status Error Code '+xhr.status+' from '+responseInfo.pathInfo.requestPath},responseInfo))}}
const extensions={}
function extensionBase(){return{init:function(api){return null},getSelectors:function(){return null},onEvent:function(name,evt){return true},transformResponse:function(text,xhr,elt){return text},isInlineSwap:function(swapStyle){return false},handleSwap:function(swapStyle,target,fragment,settleInfo){return false},encodeParameters:function(xhr,parameters,elt){return null}}}
function defineExtension(name,extension){if(extension.init){extension.init(internalAPI)}
extensions[name]=mergeObjects(extensionBase(),extension)}
function removeExtension(name){delete extensions[name]}
function getExtensions(elt,extensionsToReturn,extensionsToIgnore){if(extensionsToReturn==undefined){extensionsToReturn=[]}
if(elt==undefined){return extensionsToReturn}
if(extensionsToIgnore==undefined){extensionsToIgnore=[]}
const extensionsForElement=getAttributeValue(elt,'hx-ext')
if(extensionsForElement){forEach(extensionsForElement.split(','),function(extensionName){extensionName=extensionName.replace(/ /g,'')
if(extensionName.slice(0,7)=='ignore:'){extensionsToIgnore.push(extensionName.slice(7))
return}
if(extensionsToIgnore.indexOf(extensionName)<0){const extension=extensions[extensionName]
if(extension&&extensionsToReturn.indexOf(extension)<0){extensionsToReturn.push(extension)}}})}
return getExtensions(asElement(parentElt(elt)),extensionsToReturn,extensionsToIgnore)}
var isReady=false
getDocument().addEventListener('DOMContentLoaded',function(){isReady=true})
function ready(fn){if(isReady||getDocument().readyState==='complete'){fn()}else{getDocument().addEventListener('DOMContentLoaded',fn)}}
function insertIndicatorStyles(){if(htmx.config.includeIndicatorStyles!==false){const nonceAttribute=htmx.config.inlineStyleNonce?` nonce="${htmx.config.inlineStyleNonce}"`:''
getDocument().head.insertAdjacentHTML('beforeend','<style'+nonceAttribute+'>\
      .'+htmx.config.indicatorClass+'{opacity:0}\
      .'+htmx.config.requestClass+' .'+htmx.config.indicatorClass+'{opacity:1; transition: opacity 200ms ease-in;}\
      .'+htmx.config.requestClass+'.'+htmx.config.indicatorClass+'{opacity:1; transition: opacity 200ms ease-in;}\
      </style>')}}
function getMetaConfig(){const element=getDocument().querySelector('meta[name="htmx-config"]')
if(element){return parseJSON(element.content)}else{return null}}
function mergeMetaConfig(){const metaConfig=getMetaConfig()
if(metaConfig){htmx.config=mergeObjects(htmx.config,metaConfig)}}
ready(function(){mergeMetaConfig()
insertIndicatorStyles()
let body=getDocument().body
processNode(body)
const restoredElts=getDocument().querySelectorAll("[hx-trigger='restored'],[data-hx-trigger='restored']")
body.addEventListener('htmx:abort',function(evt){const target=evt.target
const internalData=getInternalData(target)
if(internalData&&internalData.xhr){internalData.xhr.abort()}})
const originalPopstate=window.onpopstate?window.onpopstate.bind(window):null
window.onpopstate=function(event){if(event.state&&event.state.htmx){restoreHistory()
forEach(restoredElts,function(elt){triggerEvent(elt,'htmx:restored',{document:getDocument(),triggerEvent})})}else{if(originalPopstate){originalPopstate(event)}}}
getWindow().setTimeout(function(){triggerEvent(body,'htmx:load',{})
body=null},0)})
return htmx})()