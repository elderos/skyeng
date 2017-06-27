function clear(element) {
    while (element.firstChild){
        element.removeChild(element.firstChild);
    }
}

function Cell(content, _class) {
    var element = document.createElement('div');
    element.classList.add(_class);
    element.classList.add('word-cell');
    element.textContent = content;
    return element;
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
        word_container.classList.add('word-container');
        word_container.appendChild(Cell(item.meaning_id, 'meaning'));
        word_container.appendChild(Cell(item.en, 'en'));
        word_container.appendChild(Cell(item.ru, 'ru'));
        word_container.appendChild(Cell(item.score.toFixed(2), 'score'));
        container.appendChild(word_container);
    }
    return container;
}


function load_predicted_words(){
    var seeds = document.getElementById('seed-area').value.split(/\r?\n/);
    var seeds_param = JSON.stringify(seeds);
    seeds_param = encodeURIComponent(seeds_param);

    var results_container = document.getElementById('results');
    clear(results_container);

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
    req.send(null);

}
