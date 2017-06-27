function clear(element) {
    while (element.firstChild){
        element.removeChild(element.firstChild);
    }
}


function Section(jdata){
    var container = document.createElement('div');
    container.classList.add('section-container');

    var title = document.createElement('div');
    title.classList.add('section-title');
    title.textContent = jdata.title;
    container.appendChild(title);

    for (var i = 0; i < jdata.words.length; i++){
        var item = jdata.words[i];
        var word_container = document.createElement('div');
        word_container.textContent = item.word + '\t' + item.score;
        container.appendChild(word_container);
    }
}


function load_predicted_words(){
    var seeds = document.getElementById('seed-area').textContent.split(/\r?\n/);
    var seeds_param = JSON.stringify(seeds);
    seeds_param = encodeURIComponent(seeds_param);

    var results_container = document.getElementById();

    var req = new XMLHttpRequest();
    req.open('GET', 'http://eantonov.name/skyeng/get-predicted-words?seeds=' + seeds_param, true);
    req.onreadystatechange = function () {
        if (req.readyState == XMLHttpRequest.DONE){
            if (req.status == 200) {
                var response = JSON.parse(req.responseText);
                for (var i = 0; i < response.length; i++){
                    var section = response[i];
                    var section_element = Section(section);
                    results_container.appendChild(section_element);
                }
            }
        }
    };

}
