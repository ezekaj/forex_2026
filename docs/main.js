/* ================================================================
   Ultimate Trading Bot — Shared JavaScript
   ================================================================ */

(function() {
    'use strict';

    // ── Mobile Menu Toggle ─────────────────────────────────────────
    function initMobileMenu() {
        const btn = document.getElementById('hamburger-btn');
        const menu = document.getElementById('mobile-menu');
        if (!btn || !menu) return;

        btn.addEventListener('click', function() {
            btn.classList.toggle('active');
            menu.classList.toggle('open');
        });

        menu.querySelectorAll('a').forEach(function(link) {
            link.addEventListener('click', function() {
                btn.classList.remove('active');
                menu.classList.remove('open');
            });
        });

        document.addEventListener('click', function(e) {
            if (!btn.contains(e.target) && !menu.contains(e.target)) {
                btn.classList.remove('active');
                menu.classList.remove('open');
            }
        });
    }

    // ── Scroll Reveal (IntersectionObserver) ───────────────────────
    function initScrollReveal() {
        var elements = document.querySelectorAll('.fade-in');
        if (!elements.length) return;

        if ('IntersectionObserver' in window) {
            var observer = new IntersectionObserver(function(entries) {
                entries.forEach(function(entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('visible');
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

            elements.forEach(function(el) {
                observer.observe(el);
            });
        } else {
            elements.forEach(function(el) {
                el.classList.add('visible');
            });
        }
    }

    // ── FAQ Accordion ──────────────────────────────────────────────
    function initFaqAccordion() {
        var questions = document.querySelectorAll('.faq-question');
        questions.forEach(function(btn) {
            btn.addEventListener('click', function() {
                var item = btn.closest('.faq-item');
                var wasOpen = item.classList.contains('open');

                // Close all items in same container
                var container = item.parentElement;
                container.querySelectorAll('.faq-item').forEach(function(other) {
                    other.classList.remove('open');
                });

                // Toggle clicked item
                if (!wasOpen) {
                    item.classList.add('open');
                }
            });
        });
    }

    // ── Pricing Toggle (Monthly/Annual) ────────────────────────────
    function initPricingToggle() {
        var toggleBtns = document.querySelectorAll('.pricing-toggle-btn');
        if (!toggleBtns.length) return;

        toggleBtns.forEach(function(btn) {
            btn.addEventListener('click', function() {
                var period = btn.dataset.period;

                toggleBtns.forEach(function(b) { b.classList.remove('active'); });
                btn.classList.add('active');

                // Update all price displays
                document.querySelectorAll('[data-price-monthly]').forEach(function(el) {
                    if (period === 'annual') {
                        el.textContent = el.dataset.priceAnnual;
                    } else {
                        el.textContent = el.dataset.priceMonthly;
                    }
                });

                document.querySelectorAll('[data-period-monthly]').forEach(function(el) {
                    if (period === 'annual') {
                        el.textContent = el.dataset.periodAnnual;
                    } else {
                        el.textContent = el.dataset.periodMonthly;
                    }
                });

                document.querySelectorAll('.annual-savings').forEach(function(el) {
                    el.style.display = period === 'annual' ? 'inline-flex' : 'none';
                });
            });
        });
    }

    // ── Copy to Clipboard ──────────────────────────────────────────
    function initCopyButtons() {
        document.querySelectorAll('[data-copy]').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var text = btn.dataset.copy;
                navigator.clipboard.writeText(text).then(function() {
                    var original = btn.textContent;
                    btn.textContent = 'Copied!';
                    setTimeout(function() { btn.textContent = original; }, 2000);
                });
            });
        });
    }

    // ── Smooth Scroll ──────────────────────────────────────────────
    function initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(function(link) {
            link.addEventListener('click', function(e) {
                var targetId = link.getAttribute('href');
                if (targetId === '#') return;
                var target = document.querySelector(targetId);
                if (target) {
                    e.preventDefault();
                    var offset = 70;
                    var top = target.getBoundingClientRect().top + window.pageYOffset - offset;
                    window.scrollTo({ top: top, behavior: 'smooth' });
                }
            });
        });
    }

    // ── Counter Animation ──────────────────────────────────────────
    function animateCounter(el, target, duration, prefix, suffix) {
        prefix = prefix || '';
        suffix = suffix || '';
        duration = duration || 1500;
        var start = 0;
        var startTime = null;

        function step(timestamp) {
            if (!startTime) startTime = timestamp;
            var progress = Math.min((timestamp - startTime) / duration, 1);
            var eased = 1 - Math.pow(1 - progress, 3);
            var current = Math.round(start + (target - start) * eased);
            el.textContent = prefix + current.toLocaleString() + suffix;
            if (progress < 1) requestAnimationFrame(step);
        }

        requestAnimationFrame(step);
    }

    function initCounterAnimations() {
        var counters = document.querySelectorAll('[data-counter]');
        if (!counters.length) return;

        if ('IntersectionObserver' in window) {
            var observer = new IntersectionObserver(function(entries) {
                entries.forEach(function(entry) {
                    if (entry.isIntersecting) {
                        var el = entry.target;
                        var target = parseInt(el.dataset.counter, 10);
                        var prefix = el.dataset.counterPrefix || '';
                        var suffix = el.dataset.counterSuffix || '';
                        animateCounter(el, target, 1500, prefix, suffix);
                        observer.unobserve(el);
                    }
                });
            }, { threshold: 0.3 });

            counters.forEach(function(el) { observer.observe(el); });
        }
    }

    // ── Live Price Ticker (Sample Data) ────────────────────────────
    var samplePrices = {
        BTC: { price: 97842.50, change: 2.34 },
        ETH: { price: 3456.78, change: -0.87 },
        SOL: { price: 198.45, change: 5.12 },
        BNB: { price: 612.30, change: 1.45 },
        XRP: { price: 2.87, change: -1.23 },
        ADA: { price: 0.98, change: 3.67 },
        AVAX: { price: 38.92, change: -2.10 },
        DOT: { price: 7.34, change: 0.89 }
    };

    function buildTickerHTML() {
        var items = [];
        for (var symbol in samplePrices) {
            var d = samplePrices[symbol];
            var positive = d.change >= 0;
            var color = positive ? 'color: #10B981' : 'color: #EF4444';
            var arrow = positive ? '\u25B2' : '\u25BC';
            var sign = positive ? '+' : '';
            items.push(
                '<span class="ticker-item" style="' + color + '">' +
                symbol + '/USD $' + d.price.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) +
                ' <span style="font-size:10px">' + arrow + '</span> ' + sign + d.change.toFixed(2) + '%' +
                '</span>' +
                '<span class="ticker-sep">|</span>'
            );
        }
        return items.join('') + '<span style="padding:0 2rem"></span>' + items.join('');
    }

    function initTickerTape() {
        var tracks = document.querySelectorAll('.ticker-track');
        if (!tracks.length) return;

        var html = buildTickerHTML();
        tracks.forEach(function(track) {
            track.innerHTML = html;
        });

        // Simulate small price updates
        setInterval(function() {
            for (var symbol in samplePrices) {
                var d = samplePrices[symbol];
                var variation = d.price * (Math.random() * 0.002 - 0.001);
                d.price = Math.max(0.01, d.price + variation);
                d.change = d.change + (Math.random() * 0.2 - 0.1);
            }
            var updated = buildTickerHTML();
            tracks.forEach(function(track) {
                track.innerHTML = updated;
            });
        }, 5000);
    }

    // ── Mini Chart Rendering (for landing page hero) ───────────────
    function drawMiniChart(svgId, data, color) {
        var svg = document.getElementById(svgId);
        if (!svg || !data || !data.length) return;

        var W = parseInt(svg.getAttribute('viewBox').split(' ')[2]) || 400;
        var H = parseInt(svg.getAttribute('viewBox').split(' ')[3]) || 150;
        var PAD = 10;

        var vals = data;
        var minV = Math.min.apply(null, vals);
        var maxV = Math.max.apply(null, vals);
        var range = maxV - minV || 1;

        var points = '';
        var fillPoints = '';
        for (var i = 0; i < vals.length; i++) {
            var x = PAD + (i / (vals.length - 1)) * (W - 2 * PAD);
            var y = PAD + (H - 2 * PAD) - ((vals[i] - minV) / range) * (H - 2 * PAD);
            points += x.toFixed(1) + ',' + y.toFixed(1) + ' ';
            fillPoints += x.toFixed(1) + ',' + y.toFixed(1) + ' ';
        }

        var lastX = (PAD + (vals.length - 1) / (vals.length - 1) * (W - 2 * PAD)).toFixed(1);
        fillPoints += lastX + ',' + (H - PAD) + ' ' + PAD + ',' + (H - PAD);

        color = color || '#10B981';
        svg.innerHTML =
            '<defs><linearGradient id="fill-' + svgId + '" x1="0" y1="0" x2="0" y2="1">' +
            '<stop offset="0%" stop-color="' + color + '" stop-opacity="0.25"/>' +
            '<stop offset="100%" stop-color="' + color + '" stop-opacity="0.01"/>' +
            '</linearGradient></defs>' +
            '<polygon points="' + fillPoints + '" fill="url(#fill-' + svgId + ')"/>' +
            '<polyline points="' + points.trim() + '" fill="none" stroke="' + color + '" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>';
    }

    // Generate sample chart data
    function generateChartData(points, basePrice, volatility) {
        var data = [];
        var price = basePrice;
        for (var i = 0; i < points; i++) {
            price += (Math.random() - 0.47) * volatility;
            price = Math.max(basePrice * 0.85, Math.min(basePrice * 1.2, price));
            data.push(price);
        }
        return data;
    }

    function initHeroChart() {
        var svg = document.getElementById('hero-mini-chart');
        if (!svg) return;
        var data = generateChartData(60, 97000, 500);
        drawMiniChart('hero-mini-chart', data, '#F59E0B');
    }

    // ── Backtest Simulation (for demo page) ────────────────────────
    function simulateBacktest(strategy, capital, days) {
        var equity = [capital];
        var trades = 0;
        var wins = 0;
        var maxDrawdown = 0;
        var peak = capital;
        var returns = [];

        for (var i = 0; i < days; i++) {
            var dailyReturn;
            switch (strategy) {
                case 'ma_crossover':
                    dailyReturn = (Math.random() - 0.46) * 0.03;
                    break;
                case 'rsi':
                    dailyReturn = (Math.random() - 0.47) * 0.025;
                    break;
                case 'macd':
                    dailyReturn = (Math.random() - 0.45) * 0.035;
                    break;
                case 'bollinger_bands':
                    dailyReturn = (Math.random() - 0.44) * 0.028;
                    break;
                default:
                    dailyReturn = (Math.random() - 0.46) * 0.03;
            }

            var currentEquity = equity[equity.length - 1];
            var newEquity = currentEquity * (1 + dailyReturn);
            equity.push(newEquity);
            returns.push(dailyReturn);

            if (Math.random() < 0.3) {
                trades++;
                if (dailyReturn > 0) wins++;
            }

            if (newEquity > peak) peak = newEquity;
            var dd = (peak - newEquity) / peak;
            if (dd > maxDrawdown) maxDrawdown = dd;
        }

        var totalReturn = (equity[equity.length - 1] - capital) / capital;
        var avgReturn = returns.reduce(function(a, b) { return a + b; }, 0) / returns.length;
        var stdReturn = Math.sqrt(returns.reduce(function(a, b) {
            return a + Math.pow(b - avgReturn, 2);
        }, 0) / returns.length);
        var sharpe = stdReturn > 0 ? (avgReturn / stdReturn) * Math.sqrt(252) : 0;

        return {
            equity: equity,
            totalReturn: totalReturn,
            maxDrawdown: maxDrawdown,
            sharpe: sharpe,
            winRate: trades > 0 ? wins / trades : 0,
            trades: trades,
            finalValue: equity[equity.length - 1]
        };
    }

    // ── Portfolio Display ──────────────────────────────────────────
    function formatUSD(n) {
        if (Math.abs(n) >= 1) return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        return '$' + n.toFixed(6);
    }

    // ── Demo Page Animation Controller ─────────────────────────────
    var demoController = {
        currentStep: 0,
        totalSteps: 9,
        timer: null,
        isPlaying: false,

        init: function() {
            var self = this;
            var container = document.getElementById('demo-container');
            if (!container) return;

            this.steps = container.querySelectorAll('.demo-timeline-step');
            this.progressBar = document.getElementById('demo-progress-bar');
            this.replayBtn = document.getElementById('demo-replay-btn');
            this.playPauseBtn = document.getElementById('demo-play-pause');

            if (this.replayBtn) {
                this.replayBtn.addEventListener('click', function() { self.replay(); });
            }
            if (this.playPauseBtn) {
                this.playPauseBtn.addEventListener('click', function() { self.togglePlayPause(); });
            }

            this.play();
        },

        play: function() {
            var self = this;
            this.isPlaying = true;
            if (this.playPauseBtn) this.playPauseBtn.textContent = 'Pause';
            this.showStep(this.currentStep);

            this.timer = setInterval(function() {
                self.currentStep++;
                if (self.currentStep >= self.totalSteps) {
                    self.currentStep = 0;
                    // Loop: reset all steps then restart
                    self.steps.forEach(function(s) { s.classList.remove('active', 'completed'); });
                }
                self.showStep(self.currentStep);
            }, 3000);
        },

        pause: function() {
            this.isPlaying = false;
            if (this.playPauseBtn) this.playPauseBtn.textContent = 'Play';
            clearInterval(this.timer);
        },

        togglePlayPause: function() {
            if (this.isPlaying) { this.pause(); }
            else { this.play(); }
        },

        replay: function() {
            clearInterval(this.timer);
            this.currentStep = 0;
            this.steps.forEach(function(s) { s.classList.remove('active', 'completed'); });
            this.updateProgress(0);
            this.play();
        },

        showStep: function(index) {
            var self = this;
            this.steps.forEach(function(step, i) {
                if (i < index) {
                    step.classList.add('active', 'completed');
                } else if (i === index) {
                    step.classList.add('active');
                    step.classList.remove('completed');
                } else {
                    step.classList.remove('active', 'completed');
                }
            });
            this.updateProgress((index + 1) / this.totalSteps * 100);

            // Trigger step-specific animations
            this.animateStep(index);
        },

        updateProgress: function(pct) {
            if (this.progressBar) {
                this.progressBar.style.width = pct + '%';
            }
        },

        animateStep: function(index) {
            switch (index) {
                case 0: this.animatePriceStream(); break;
                case 2: this.animateCandlesticks(); break;
                case 4: this.animateBuySignal(); break;
                case 6: this.animateProfitCounter(); break;
                case 7: this.animateSellSignal(); break;
                case 8: this.animateDashboard(); break;
            }
        },

        animatePriceStream: function() {
            var el = document.getElementById('demo-price-stream');
            if (!el) return;
            var prices = [97842, 97856, 97831, 97890, 97912, 97945, 97923, 97967];
            var i = 0;
            var interval = setInterval(function() {
                if (i >= prices.length) { clearInterval(interval); return; }
                el.textContent = '$' + prices[i].toLocaleString();
                el.style.color = i > 0 && prices[i] > prices[i-1] ? '#10B981' : '#EF4444';
                i++;
            }, 300);
        },

        animateCandlesticks: function() {
            var candles = document.querySelectorAll('#demo-candles .candle');
            candles.forEach(function(c, i) {
                c.style.opacity = '0';
                setTimeout(function() {
                    c.style.opacity = '1';
                    c.style.transition = 'opacity 0.3s ease';
                }, i * 100);
            });
        },

        animateBuySignal: function() {
            var signal = document.getElementById('demo-buy-signal');
            if (signal) {
                signal.style.opacity = '0';
                setTimeout(function() {
                    signal.style.opacity = '1';
                    signal.style.transition = 'opacity 0.4s ease';
                }, 200);
            }
        },

        animateSellSignal: function() {
            var signal = document.getElementById('demo-sell-signal');
            if (signal) {
                signal.style.opacity = '0';
                setTimeout(function() {
                    signal.style.opacity = '1';
                    signal.style.transition = 'opacity 0.4s ease';
                }, 200);
            }
        },

        animateProfitCounter: function() {
            var el = document.getElementById('demo-profit');
            if (!el) return;
            var target = 347.82;
            var current = 0;
            var step = target / 30;
            var interval = setInterval(function() {
                current += step;
                if (current >= target) {
                    current = target;
                    clearInterval(interval);
                }
                el.textContent = '+$' + current.toFixed(2);
            }, 50);
        },

        animateDashboard: function() {
            var metrics = document.querySelectorAll('#demo-dashboard .metric-value');
            var values = ['67.4%', '1.83', '+12.4%', '2.1'];
            metrics.forEach(function(el, i) {
                el.style.opacity = '0';
                setTimeout(function() {
                    el.textContent = values[i];
                    el.style.opacity = '1';
                    el.style.transition = 'opacity 0.4s ease';
                }, i * 200);
            });
        }
    };

    // ── IBAN Toggle ────────────────────────────────────────────────
    window.toggleIban = function() {
        var content = document.getElementById('iban-content');
        var arrow = document.getElementById('iban-arrow');
        if (content) {
            content.classList.toggle('open');
            if (arrow) {
                arrow.style.transform = content.classList.contains('open') ? 'rotate(180deg)' : 'rotate(0deg)';
            }
        }
    };

    // ── Initialize Everything ──────────────────────────────────────
    document.addEventListener('DOMContentLoaded', function() {
        initMobileMenu();
        initScrollReveal();
        initFaqAccordion();
        initPricingToggle();
        initCopyButtons();
        initSmoothScroll();
        initCounterAnimations();
        initTickerTape();
        initHeroChart();

        // Init demo if on demo page
        if (document.getElementById('demo-container')) {
            demoController.init();
        }
    });

    // Expose for external use
    window.UTB = {
        simulateBacktest: simulateBacktest,
        drawMiniChart: drawMiniChart,
        generateChartData: generateChartData,
        formatUSD: formatUSD,
        animateCounter: animateCounter,
        demoController: demoController
    };

})();
