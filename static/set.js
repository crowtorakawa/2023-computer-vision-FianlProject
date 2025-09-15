import data from '../update.json' 
let hintPoint = document.querySelector('.row').children[1]
console.log(jsonData)
hintPoint.innerHTML=`
<p>${data.staff}已經在${data.time}${data.state}了</p>
`