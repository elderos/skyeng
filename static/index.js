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


function load_from_params(){
    var url = window.location.href;
    var params_index = url.indexOf('?');
    if (!params_index || params_index < 0){
        return;
    }

    var params = url.substring(url.indexOf('?') + 1);
    var kv = params.split('&');
    var params_dict = {
        seeds: ''
    };
    kv.forEach(function(x){
        var arr = x.split('=');
        var key = arr[0];
        params_dict[key] = decodeURIComponent(arr[1]);
    });

    load_predicted_words(params_dict.seeds)
}


function load_predicted_words(seeds_param){
    var results_container = document.getElementById('results');
    clear(results_container);

    var seeds_textarea = document.getElementById('seed-area');
    seeds_textarea.value = '';

    if (!seeds_param){
        return;
    }

    var seeds = JSON.parse(decodeURIComponent(seeds_param));
    seeds_textarea.value = seeds.join('\n');


    var req = new XMLHttpRequest();
    req.open('GET', 'get-predicted-words?seeds=' + seeds_param, true);
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


function on_predict_btn(){
    var seeds = document.getElementById('seed-area').value.split(/\r?\n/);
    var seeds_param = JSON.stringify(seeds);
    seeds_param = encodeURIComponent(seeds_param);

    var port = '';
    if (window.location.port != 80){
        port = ':' + window.location.port
    }

    window.history.pushState(
        seeds_param,
        'Word predict',
        'http://' + window.location.hostname + port + '/skyeng/?seeds=' + seeds_param
    );
    load_predicted_words(seeds_param);
}

function words_from_source(source){
    var req = new XMLHttpRequest();
    req.open('GET', source, true);
    var textarea = document.getElementById('seed-area');
    textarea.value = '';
    req.onreadystatechange = function () {
        if (req.readyState == XMLHttpRequest.DONE){
            if (req.status == 200) {
                var words = JSON.parse(req.responseText);
                textarea.value = words.join('\n');
                on_predict_btn();
            } else {
                textarea.value = 'Error while requesting server';
            }
        }
    };
    req.send(null);
}

function on_random_lesson_btn(){
    words_from_source('random-lesson');
}

function on_random_user_btn(){
    words_from_source('random-user');
}


window.addEventListener('popstate', function (e) {
    load_from_params();
});

window.addEventListener('load', function () {
    load_from_params();
});
