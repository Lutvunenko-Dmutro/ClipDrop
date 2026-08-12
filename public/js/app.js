        const tg = window.Telegram.WebApp;
        tg.expand(); // Розгортаємо на весь екран
        
        // Встановлюємо кольори під тему (якщо є)
        tg.setHeaderColor('#09090b');
        tg.setBackgroundColor('#09090b');

        let selectedUrls = new Set();
        
        function search() {
            const query = document.getElementById('searchInput').value.trim();
            if(!query) return;

            // Ховаємо пустий стан, показуємо лоадер
            document.getElementById('emptyState').style.display = 'none';
            document.getElementById('gallery').innerHTML = '';
            document.getElementById('loader').style.display = 'block';

            // Даємо легку вібрацію
            tg.HapticFeedback.impactOccurred('light');

            fetch(`/api/search?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    document.getElementById('loader').style.display = 'none';
                    if (data.videos.length === 0) {
                        showError("Нічого не знайдено 😔");
                    } else {
                        renderGallery(data.videos);
                    }
                })
                .catch(err => {
                    document.getElementById('loader').style.display = 'none';
                    showError("Помилка завантаження. Спробуй ще раз.");
                });
        }

        function showError(msg) {
            const empty = document.getElementById('emptyState');
            empty.style.display = 'flex';
            empty.querySelector('h2').textContent = "Упс!";
            empty.querySelector('p').textContent = msg;
        }

        function renderGallery(videos) {
            const gallery = document.getElementById('gallery');
            
            videos.forEach((vid, index) => {
                const card = document.createElement('div');
                card.className = 'video-card';
                // Анімація каскадом
                card.style.animationDelay = `${index * 0.05}s`;
                
                if (selectedUrls.has(vid.hd_url)) {
                    card.classList.add('selected');
                }

                card.innerHTML = `
                    <video src="${vid.sd_url}" autoplay loop muted playsinline disablePictureInPicture></video>
                    <div class="video-info">
                        <div class="video-author">📸 ${vid.author}</div>
                    </div>
                    <div class="checkmark-wrapper">
                        <svg class="checkmark-icon" viewBox="0 0 24 24">
                            <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                    </div>
                `;
                
                card.onclick = () => toggleSelect(card, vid.hd_url);
                gallery.appendChild(card);
            });
        }

        function toggleSelect(card, hd_url) {
            tg.HapticFeedback.selectionChanged();
            
            if (selectedUrls.has(hd_url)) {
                selectedUrls.delete(hd_url);
                card.classList.remove('selected');
            } else {
                selectedUrls.add(hd_url);
                card.classList.add('selected');
            }
            updateMainButton();
        }

        function updateMainButton() {
            if (selectedUrls.size > 0) {
                tg.MainButton.text = `ЗАВАНТАЖИТИ ZIP (${selectedUrls.size})`;
                tg.MainButton.color = '#6366f1';
                tg.MainButton.textColor = '#ffffff';
                if (!tg.MainButton.isVisible) tg.MainButton.show();
            } else {
                tg.MainButton.hide();
            }
        }

        tg.MainButton.onClick(() => {
            tg.HapticFeedback.impactOccurred('medium');
            const urls = Array.from(selectedUrls);
            tg.sendData(JSON.stringify({ action: "download_zip", urls: urls }));
        });

        // Запуск пошуку клавішею Enter
        document.getElementById('searchInput').addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                search();
                // Ховаємо клавіатуру
                this.blur(); 
            }
        });
