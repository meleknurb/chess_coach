// static/js/dashboard.js

const DEFAULT_LIMIT = 5;

document.addEventListener("DOMContentLoaded", function () {
    let currentOffset = DEFAULT_LIMIT; 

    const searchInput = document.querySelector(".search-input");
    const gameTableBody = document.querySelector(".game-table tbody");
    const loadMoreBtn = document.getElementById('load-more-btn');
    const collapseBtn = document.getElementById('collapse-btn');
    const loadingMessage = document.querySelector('.loading-message');

    if (typeof loadMoreGamesUrl === 'undefined' || typeof searchGamesUrl === 'undefined' || typeof analyzeGameUrl === 'undefined') {
        console.error("ERROR: Django URL variables are NOT defined globally.");
        return;
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                let cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrfToken = getCookie('csrftoken');

    function createGameRow(game) {
        let resultClass;
        if (game.result_description.includes("Win")) {
            resultClass = "result-win";
        } else if (game.result_description.includes("Loss")) {
            resultClass = "result-loss";
        } else {
            resultClass = "result-draw";
        }

        return `
            <tr>
                <td>${game.date}</td>
                <td>${game.time_control}</td>
                <td class="player-details-cell">
                    <div class="player-line white-player">
                        <span class="color-indicator"></span>
                        <span>${game.player_top}</span>
                    </div>
                    <div class="player-line black-player">
                        <span class="color-indicator"></span>
                        <span>${game.player_bottom}</span>
                    </div>
                </td>
                <td class="${resultClass}">${game.result_description}</td>
                <td>${game.moves_count}</td>
                <td>
                    <form action="${analyzeGameUrl}" method="post">
                        <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                        <input type="hidden" name="game_id" value="${game.pk || ''}">
                        <button type="submit" class="btn small-btn analyze-btn">Analyze</button>
                    </form>
                </td>
            </tr>
        `;
    }
    
    function updateControlButtons() {
        const totalGamesOnScreen = gameTableBody.querySelectorAll('tr').length;
        
        if (totalGamesOnScreen > DEFAULT_LIMIT && totalGamesOnScreen > 0) {
            collapseBtn.style.display = 'inline-block';
        } else {
            collapseBtn.style.display = 'none';
        }

        const isSearching = searchInput.value.trim() !== '';
        if (isSearching) {
            loadMoreBtn.style.display = 'none';
        } else {
            loadMoreBtn.style.display = 'inline-block';
        }
    }


    function performSearch(query) {
        loadingMessage.style.display = 'block';
        gameTableBody.innerHTML = ''; 

        fetch(`${searchGamesUrl}?query=${encodeURIComponent(query)}`)
            .then(res => res.json())
            .then(data => {
                loadingMessage.style.display = 'none';

                if (data.games.length === 0) {
                    gameTableBody.innerHTML = `<tr><td colspan="6" class="no-games">No games found.</td></tr>`;
                    currentOffset = 0;
                    return;
                }

                data.games.forEach(game => {
                    gameTableBody.insertAdjacentHTML('beforeend', createGameRow(game));
                });
                
                currentOffset = data.games.length;
                updateControlButtons(); 
            })
            .catch(err => {
                console.error("Search failed:", err);
                loadingMessage.style.display = 'none';
            })
            .finally(() => {
                updateControlButtons();
            });
    }

    loadMoreBtn.addEventListener('click', function() {
        if (searchInput.value.trim() !== '') return; 

        loadingMessage.style.display = 'block';
        loadMoreBtn.disabled = true; 

        const url = `${loadMoreGamesUrl}?offset=${currentOffset}`;

        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.games && data.games.length > 0) {
                    data.games.forEach(game => {
                        gameTableBody.insertAdjacentHTML('beforeend', createGameRow(game));
                    });
                    
                    currentOffset += data.games.length;
                    
                    const newUrl = `${window.location.pathname}?offset=${currentOffset}`;
                    window.history.pushState({count: currentOffset}, '', newUrl);
                    
                } else {
                    alert("No more games found in your history.");
                }
                
                updateControlButtons();
            })
            .catch(error => {
                console.error('Error loading more games:', error);
                alert('An error occurred while loading games.');
            })
            .finally(() => {
                loadingMessage.style.display = 'none';
                loadMoreBtn.disabled = false;
            });
    });

    collapseBtn.addEventListener('click', function() {
        const rows = gameTableBody.querySelectorAll('tr');
        
        if (rows.length > DEFAULT_LIMIT) {
            for (let i = 0; i < DEFAULT_LIMIT; i++) {
                if (gameTableBody.lastElementChild) {
                    gameTableBody.removeChild(gameTableBody.lastElementChild);
                }
            }
            
            currentOffset = gameTableBody.querySelectorAll('tr').length;
            const rowsAfterCollapse = currentOffset;

            if (rowsAfterCollapse === DEFAULT_LIMIT) {
                window.history.pushState(null, '', window.location.pathname); 
            } else {
                const newUrl = `${window.location.pathname}?offset=${rowsAfterCollapse}`;
                window.history.pushState({count: rowsAfterCollapse}, '', newUrl);
            }
        }

        updateControlButtons();
    });


    searchInput.addEventListener("keypress", function(e) {
        if (e.key === "Enter") {
            e.preventDefault();
            const query = searchInput.value.trim();
            if (!query) {
                location.reload(); 
                return;
            }

            const newUrl = `${window.location.pathname}?query=${encodeURIComponent(query)}`;
            window.history.pushState({path: newUrl}, '', newUrl);

            loadMoreBtn.style.display = 'none';
            collapseBtn.style.display = 'none';

            performSearch(query);
        }
    });

    const urlParams = new URLSearchParams(window.location.search);
    const initialQuery = urlParams.get('query');
    const initialOffsetParam = urlParams.get('offset'); 
    const rowsOnScreen = gameTableBody.querySelectorAll('tr').length; 

    if (initialQuery) {
        searchInput.value = initialQuery;
        performSearch(initialQuery); 
    } 
    else {
        if (initialOffsetParam && rowsOnScreen === DEFAULT_LIMIT) {
            
            const cleanUrl = window.location.pathname; 
            window.history.replaceState(null, '', cleanUrl);
            currentOffset = DEFAULT_LIMIT; 
            
        } else if (initialOffsetParam && rowsOnScreen > DEFAULT_LIMIT) {
             currentOffset = rowsOnScreen;
        }

        updateControlButtons();
    }


    window.addEventListener('popstate', function(e) {
        const params = new URLSearchParams(window.location.search);
        const query = params.get('query');

        if (query) {
            searchInput.value = query;
            performSearch(query);
        } else {
            searchInput.value = '';
            location.reload(); 
        }
    });

});