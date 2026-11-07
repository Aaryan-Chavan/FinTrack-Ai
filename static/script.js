const API_BASE = '/api/v1';
let token = localStorage.getItem('token');
let pieChart1Instance = null;
let barChartInstance = null;

// ==========================================
// SECURITY & XSS SANITIZATION
// ==========================================
function escapeHTML(str) {
    if (str === null || str === undefined) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

function getInitials(name) {
    if (!name) return 'U';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
}

// ==========================================
// INITIALIZATION
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    const dateInput = document.getElementById('date');
    if (dateInput) dateInput.valueAsDate = new Date();
    
    // Set current month string in Dashboard header
    const d = new Date();
    const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    const monthLabel = document.getElementById('currentMonthLabel');
    if (monthLabel) monthLabel.innerText = `${months[d.getMonth()]} ${d.getFullYear()}`;

    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (savedTheme === 'light') {
        document.documentElement.classList.remove('dark');
        document.getElementById('theme-icon').innerText = 'dark_mode';
    } else {
        document.documentElement.classList.add('dark');
        document.getElementById('theme-icon').innerText = 'light_mode';
    }

    const storedUsername = localStorage.getItem('username');
    const storedFullName = localStorage.getItem('fullname');
    
    if (token) {
        if (storedUsername) updateUsernameUI(storedUsername, storedFullName);
        onLoginSuccess();
    } else {
        showAuthModal();
    }
});

function showPopup(msg, type = 'success') {
    const toast = document.getElementById("popup");
    if (!toast) return;
    toast.className = `toast-popup ${type}`;
    toast.innerHTML = `<span class="material-symbols-outlined">${type === 'success' ? 'check_circle' : 'error'}</span><span>${escapeHTML(msg)}</span>`;
    toast.style.display = 'flex';
    setTimeout(() => { toast.style.display = 'none'; }, 4000);
}

function toggleTheme() {
    const html = document.documentElement;
    const themeIcon = document.getElementById('theme-icon');
    if (html.classList.contains('dark')) {
        html.classList.remove('dark');
        themeIcon.innerText = 'dark_mode';
        localStorage.setItem('theme', 'light');
    } else {
        html.classList.add('dark');
        themeIcon.innerText = 'light_mode';
        localStorage.setItem('theme', 'dark');
    }
    if (token) loadAnalytics();
}

function switchTab(tabId) {
    document.querySelectorAll('.page-view').forEach(view => view.classList.add('hidden'));
    const target = document.getElementById(`view-${tabId}`);
    if (target) target.classList.remove('hidden');

    document.querySelectorAll('.nav-item').forEach(item => {
        if (item.getAttribute('data-tab-id') === tabId) {
            item.className = 'nav-item active-nav w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-200 bg-primary-container text-on-primary-container font-semibold shadow-sm';
        } else {
            item.className = 'nav-item w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-200 text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high/60';
        }
    });

    if (tabId === 'dashboard') { loadTransactions(); loadAnalytics(); }
    if (tabId === 'salary-planner') loadPlanner();
    if (tabId === 'month-closure') loadClosure();
    if (tabId === 'explore-products') loadProducts();
    
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ==========================================
// API WRAPPER
// ==========================================
async function fetchAPI(endpoint, options = {}) {
    if (!options.headers) options.headers = {};
    options.headers['Content-Type'] = 'application/json';
    if (token) options.headers['Authorization'] = `Bearer ${token}`;

    try {
        const res = await fetch(`${API_BASE}${endpoint}`, options);
        if (res.status === 401 && !endpoint.startsWith('/auth/')) {
            logoutUser();
            throw new Error("Session expired.");
        }
        const text = await res.text();
        let data = {};
        try { data = text ? JSON.parse(text) : {}; } catch (e) { data = { error: `HTTP ${res.status}` }; }
        return { res, data };
    } catch (err) {
        showPopup(err.message || "Network error.", "error");
        return { res: { ok: false }, data: { error: err.message || "Network error." } };
    }
}

// ==========================================
// AUTHENTICATION & PROFILE
// ==========================================
function updateUsernameUI(username, fullname = null) {
    const displayName = fullname || localStorage.getItem('fullname') || username;
    
    const displayUser = document.getElementById('displayUsername');
    if (displayUser) displayUser.innerText = displayName;
    
    const prefUser = document.getElementById('prefUsername');
    const prefFull = document.getElementById('prefFullName');
    const profName = document.getElementById('profileFullName');
    const profHandle = document.getElementById('profileHandle');
    
    const profInitials = document.getElementById('profileInitials');
    const dockInitials = document.getElementById('dockInitials');

    if (prefUser) prefUser.value = `@${username}`;
    if (prefFull) prefFull.value = displayName;
    if (profName) profName.innerText = displayName;
    if (profHandle) profHandle.innerText = `@${username} • FinTrack Core Controller`;
    
    const initials = getInitials(displayName);
    if (profInitials) profInitials.innerText = initials;
    if (dockInitials) dockInitials.innerText = initials;
}

let authMode = 'login';
function setAuthMode(mode) {
    authMode = mode;
    const btnLogin = document.getElementById('auth-tab-login');
    const btnRegister = document.getElementById('auth-tab-register');
    const actionBtn = document.getElementById('auth-action-btn');
    const nameField = document.getElementById('register-name-field');

    if (mode === 'register') {
        if (btnRegister) btnRegister.className = 'px-3 py-1.5 rounded-lg text-xs font-bold transition-all bg-primary-container text-on-primary-container';
        if (btnLogin) btnLogin.className = 'px-3 py-1.5 rounded-lg text-xs font-bold transition-all text-on-surface-variant hover:text-on-surface';
        if (actionBtn) actionBtn.innerHTML = '<span class="material-symbols-outlined text-lg">person_add</span><span>Create Enterprise Account</span>';
        if (nameField) nameField.classList.remove('hidden');
    } else {
        if (btnLogin) btnLogin.className = 'px-3 py-1.5 rounded-lg text-xs font-bold transition-all bg-primary-container text-on-primary-container';
        if (btnRegister) btnRegister.className = 'px-3 py-1.5 rounded-lg text-xs font-bold transition-all text-on-surface-variant hover:text-on-surface';
        if (actionBtn) actionBtn.innerHTML = '<span class="material-symbols-outlined text-lg">login</span><span>Authenticate to Dashboard</span>';
        if (nameField) nameField.classList.add('hidden');
    }
}

async function performAuthentication() {
    const uname = document.getElementById('username').value.trim();
    const pass = document.getElementById('password').value.trim();
    const fname = document.getElementById('fullname') ? document.getElementById('fullname').value.trim() : '';
    
    if (!uname || !pass) return showPopup("Username & Password required", 'error');

    let payload = { username: uname, password: pass };
    
    if (authMode === 'register') {
        if (!fname) return showPopup("Full Legal Name is required", 'error');
        // Include full name in payload in case backend supports it
        payload.full_name = fname;
    }

    const endpoint = authMode === 'login' ? '/auth/login' : '/auth/register';
    const { res, data } = await fetchAPI(endpoint, {
        method: 'POST',
        body: JSON.stringify(payload)
    });

    if (res.ok) {
        token = data.token;
        localStorage.setItem('token', token);
        localStorage.setItem('username', data.username);
        
        // Save the full name. If logging in, try to get it from data.full_name, otherwise fallback to username
        const finalName = authMode === 'register' ? fname : (data.full_name || data.username);
        localStorage.setItem('fullname', finalName);
        
        updateUsernameUI(data.username, finalName);
        
        document.getElementById('password').value = ""; 
        hideAuthModal();
        onLoginSuccess();
    } else {
        showPopup(data.error || "Authentication failed", 'error');
    }
}

function saveProfileChanges() {
    const newName = document.getElementById('prefFullName').value.trim();
    if (newName) {
        localStorage.setItem('fullname', newName);
        updateUsernameUI(localStorage.getItem('username'), newName);
        showPopup('Preferences saved successfully!', 'success');
    } else {
        showPopup('Full name cannot be empty', 'error');
    }
}

function showAuthModal() {
    const modal = document.getElementById('auth-modal');
    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }
}

function hideAuthModal() {
    const modal = document.getElementById('auth-modal');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
}

function onLoginSuccess() {
    const nav = document.getElementById('appNavigation') || document.querySelector('nav');
    if (nav) nav.style.display = 'block';
    
    const dock = document.getElementById('userProfileDock');
    if (dock) dock.style.display = 'block';
    
    switchTab('dashboard');
}

function logoutUser() {
    token = null;
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('fullname');
    
    const nav = document.getElementById('appNavigation') || document.querySelector('nav');
    if (nav) nav.style.display = 'none';
    const dock = document.getElementById('userProfileDock');
    if (dock) dock.style.display = 'none';
    
    if (pieChart1Instance) { pieChart1Instance.destroy(); pieChart1Instance = null; }
    if (barChartInstance) { barChartInstance.destroy(); barChartInstance = null; }
    
    showAuthModal();
    showPopup("Logged out safely.", "success");
}

// ==========================================
// TRANSACTIONS
// ==========================================
async function addTransaction() {
    const cat = document.getElementById('category').value.trim();
    const amt = document.getElementById('amount').value;
    const typ = document.getElementById('type').value;
    const dt = document.getElementById('date').value;

    if (!cat || !amt || !dt) return showPopup("Fill all fields", 'error');

    const { res, data } = await fetchAPI('/transactions', {
        method: 'POST',
        body: JSON.stringify({ category: cat, amount: amt, type: typ, date: dt })
    });

    if (res.ok) {
        showPopup("Transaction recorded", 'success');
        document.getElementById('amount').value = "";
        document.getElementById('category').value = "";
        loadTransactions();
        loadAnalytics();
    } else {
        showPopup(data.error || "Failed to add", 'error');
    }
}

async function loadTransactions() {
    const filterEl = document.getElementById('filterType');
    const filterType = filterEl ? filterEl.value : '';
    const { res, data } = await fetchAPI(`/transactions?type=${encodeURIComponent(filterType)}`);
    
    if (res.ok && Array.isArray(data)) {
        const list = document.getElementById('transactionList');
        if (!list) return;
        let html = "";
        data.forEach(t => {
            const isExpense = t.type === 'expense';
            html += `
            <tr class="hover:bg-surface-variant/20 transition-colors">
                <td class="py-3 flex items-center gap-3">
                    <div class="w-8 h-8 rounded-lg ${isExpense ? 'bg-error/10 text-error' : 'bg-tertiary/10 text-tertiary'} flex items-center justify-center font-bold">
                        <span class="material-symbols-outlined text-sm">${isExpense ? 'arrow_downward' : 'arrow_upward'}</span>
                    </div>
                    <div>
                        <p class="font-semibold text-on-surface">${escapeHTML(t.category)}</p>
                        <p class="text-[11px] text-outline">${escapeHTML(t.date)}</p>
                    </div>
                </td>
                <td class="py-3"><span class="px-2 py-0.5 rounded text-[11px] ${isExpense ? 'bg-surface-variant text-on-surface' : 'bg-primary-container/20 text-primary'} font-semibold">${isExpense ? 'Debit' : 'Credit'}</span></td>
                <td class="py-3 text-right tabular-val font-bold ${isExpense ? 'text-error' : 'text-tertiary'}">${isExpense ? '-' : '+'}₹${parseFloat(t.amount).toLocaleString('en-IN')}</td>
                <td class="py-3 text-right">
                    <button onclick="delTx(${t.id})" class="text-outline hover:text-error transition-colors"><span class="material-symbols-outlined text-sm">delete</span></button>
                </td>
            </tr>`;
        });
        list.innerHTML = html;
    }
}

async function delTx(id) {
    if(!confirm("Delete transaction?")) return;
    const {res} = await fetchAPI(`/transactions/${id}`, {method: 'DELETE'});
    if(res.ok){ loadTransactions(); loadAnalytics(); }
}

// ==========================================
// ANALYTICS & CHARTS
// ==========================================
async function loadAnalytics() {
    const { res, data } = await fetchAPI('/analytics');
    if (!res.ok) return;

    const incVal = parseFloat(data.income) || 0;
    const expVal = parseFloat(data.expense) || 0;
    const balVal = parseFloat(data.balance) || 0;
    
    const incEl = document.getElementById('income');
    const expEl = document.getElementById('expense');
    const balEl = document.getElementById('balance');
    const srEl = document.getElementById('savingsRate');
    
    if (incEl) incEl.innerText = `₹${incVal.toLocaleString('en-IN')}`;
    if (expEl) expEl.innerText = `₹${expVal.toLocaleString('en-IN')}`;
    if (balEl) balEl.innerText = `₹${balVal.toLocaleString('en-IN')}`;
    if (srEl) {
        const sr = incVal > 0 ? ((balVal / incVal) * 100).toFixed(1) : 0;
        srEl.innerText = `${sr}%`;
    }

    const isDark = document.documentElement.classList.contains('dark');
    const textColor = isDark ? '#dbe1ff' : '#0f172a';
    if (window.Chart) {
        Chart.defaults.color = textColor;
        Chart.defaults.font.family = "'Inter', sans-serif";
    }

    if (pieChart1Instance) pieChart1Instance.destroy();
    if (barChartInstance) barChartInstance.destroy();

    const hasData = Array.isArray(data.pie) && data.pie.length > 0;

    // ====================================
    // DYNAMIC TOP 3 CATEGORIES FOOTER
    // ====================================
    const topCatsFooter = document.getElementById('topCategoriesFooter');
    if (topCatsFooter) {
        if (hasData) {
            // Sort user categories by total descending
            const sortedCats = [...data.pie].sort((a, b) => parseFloat(b.total) - parseFloat(a.total));
            const top3 = sortedCats.slice(0, 3); // Get the top 3 biggest expenses
            
            let footerHtml = '';
            top3.forEach(cat => {
                footerHtml += `
                <div>
                    <p class="font-label-caps text-outline text-[11px] font-bold uppercase truncate px-1" title="${escapeHTML(cat.category)}">${escapeHTML(cat.category)}</p>
                    <p class="currency-figure font-bold text-on-surface text-base mt-1">₹${parseFloat(cat.total).toLocaleString('en-IN')}</p>
                </div>`;
            });
            topCatsFooter.innerHTML = footerHtml;
        } else {
            topCatsFooter.innerHTML = `
                <div class="col-span-3 text-outline text-xs mt-4">No expense data recorded yet.</div>
            `;
        }
    }

    // ====================================
    // PIE CHART
    // ====================================
    const pieCtx = document.getElementById("pieChart1");
    if (pieCtx && window.Chart) {
        const pieContainer = pieCtx.parentElement;
        let centerText = document.getElementById('donutCenterText');
        if (!centerText) {
            centerText = document.createElement('div');
            centerText.id = 'donutCenterText';
            centerText.className = 'absolute inset-0 flex flex-col items-center justify-center pointer-events-none pb-8';
            pieContainer.appendChild(centerText);
        }
        centerText.innerHTML = `
            <span class="text-[10px] text-outline uppercase font-bold tracking-widest mt-4">Total Burn</span>
            <span class="text-2xl font-bold text-on-surface">₹${expVal.toLocaleString('en-IN')}</span>
        `;

        // Dynamically build arrays to include the Available Balance
        let pieLabels = [];
        let pieData = [];
        let pieColors = [];

        if (hasData) {
            pieLabels = data.pie.map(x => x.category);
            pieData = data.pie.map(x => parseFloat(x.total));
            // Base colors for expense categories
            pieColors = ['#4d8eff', '#03b5d3', '#8b5cf6', '#ffb4ab', '#f59e0b', '#dbe1ff']; 
            
            // Append Available Balance if the user is not in a deficit
            if (balVal > 0) {
                pieLabels.push('Available Balance');
                pieData.push(balVal);
                pieColors.push('#4edea3'); // Green color for positive surplus
            }
        } else {
            // Fallback if no transactions exist yet
            pieLabels = ['Available Balance', 'Expense'];
            pieData = [balVal > 0 ? balVal : 0, expVal];
            pieColors = ['#4edea3', '#ffb4ab'];
        }

        pieChart1Instance = new Chart(pieCtx, {
            type: 'doughnut',
            data: {
                labels: pieLabels,
                datasets: [{
                    data: pieData,
                    backgroundColor: pieColors,
                    borderWidth: 2,
                    borderColor: isDark ? '#171e37' : '#ffffff',
                    hoverOffset: 4
                }]
            },
            options: { 
                responsive: true, 
                maintainAspectRatio: false, 
                cutout: '82%',
                plugins: { 
                    legend: { 
                        position: 'bottom', 
                        labels: { usePointStyle: true, boxWidth: 8, padding: 12, font: { size: 10 } } 
                    } 
                }
            }
        });
    }

    // ====================================
    // STITCH-STYLED SEQUENTIAL WAVE CHART
    // ====================================
    const barCtx = document.getElementById("barChart");
    if (barCtx && window.Chart) {
        
        // Fetch ALL transactions without filtering out past months
        const txRes = await fetchAPI('/transactions');
        
        let waveLabels = [];
        let waveData = [];
        let txAmounts = []; // Array to hold actual transaction amounts for the tooltip
        let pointRadii = [];
        let pointColors = [];
        let isCredit = []; 

        if (txRes.res.ok && Array.isArray(txRes.data) && txRes.data.length > 0) {
            
            // 1. Sort chronologically (oldest to newest) 
            const sortedTx = txRes.data.slice().sort((a, b) => {
                const dateDiff = new Date(a.date) - new Date(b.date);
                if (dateDiff !== 0) return dateDiff;
                return a.id - b.id; 
            });
            
            let runningBalance = 0; // Initialize running balance
            
            // 2. Add a hidden "Start" anchor at value 0
            waveLabels.push('');
            waveData.push(0);
            txAmounts.push(0);
            pointRadii.push(0);
            pointColors.push('transparent');
            isCredit.push(false);

            // 3. Add the actual transactions and calculate cumulative balance
            sortedTx.forEach(tx => {
                const amt = parseFloat(tx.amount);
                const isIncome = tx.type === 'income';
                
                if (isIncome) {
                    runningBalance += amt;
                } else {
                    runningBalance -= amt;
                }
                
                waveLabels.push(tx.date + ' ' + tx.category); 
                waveData.push(runningBalance); // Plot the running balance
                txAmounts.push(amt);           // Store actual tx amount for tooltip
                pointRadii.push(6); 
                pointColors.push(isIncome ? '#4edea3' : '#3B82F6'); 
                isCredit.push(isIncome);
            });

            // 4. Add a hidden "End" anchor level with the final balance
            waveLabels.push('');
            waveData.push(runningBalance);
            txAmounts.push(0);
            pointRadii.push(0);
            pointColors.push('transparent');
            isCredit.push(false);
        } else {
            // Fallback for zero transactions
            waveLabels = ["", "No Data", ""];
            waveData = [0, 0.1, 0];
            txAmounts = [0, 0, 0];
            pointRadii = [0, 0, 0];
            pointColors = ['transparent', 'transparent', 'transparent'];
            isCredit = [false, false, false];
        }

        const ctx = barCtx.getContext("2d");
        let fillGradient = ctx.createLinearGradient(0, 0, 0, barCtx.parentElement.offsetHeight || 300);
        fillGradient.addColorStop(0, 'rgba(6, 182, 212, 0.45)');
        fillGradient.addColorStop(1, 'rgba(6, 182, 212, 0.00)');

        const dynamicWidth = Math.max(600, waveLabels.length * 200);
        barCtx.parentElement.style.minWidth = `${dynamicWidth}px`;

        let lineGradient = ctx.createLinearGradient(0, 0, dynamicWidth, 0);
        lineGradient.addColorStop(0, '#06B6D4'); 
        lineGradient.addColorStop(0.5, '#3B82F6'); 
        lineGradient.addColorStop(1, '#4edea3'); 

        barChartInstance = new Chart(barCtx, {
            type: 'line',
            data: {
                labels: waveLabels,
                datasets: [{
                    label: 'Available Balance',
                    data: waveData,
                    borderColor: lineGradient,
                    borderWidth: 4,
                    backgroundColor: fillGradient,
                    fill: true,
                    tension: 0.4, 
                    pointBackgroundColor: pointColors, 
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: pointRadii, 
                    pointHoverRadius: 8
                }]
            },
            options: { 
                responsive: true, 
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        // Dynamically adjust tooltip background and border for readability in Light Mode
                        backgroundColor: isDark ? 'rgba(30, 41, 59, 0.95)' : 'rgba(255, 255, 255, 0.95)',
                        borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
                        borderWidth: 1,
                        titleColor: isDark ? '#94a3b8' : '#64748b',
                        // Set the footer (Balance) text color strictly based on the theme
                        footerColor: isDark ? '#ffffff' : '#0b132b',
                        footerMarginTop: 4,
                        footerFont: { weight: 'normal', size: 13 },
                        bodyFont: { size: 13 },
                        padding: 10,
                        callbacks: {
                            // Colors ONLY the Transaction string (Green/Red)
                            labelTextColor: function(context) {
                                if (pointRadii[context.dataIndex] === 0) return 'transparent';
                                return isCredit[context.dataIndex] ? '#4edea3' : '#ffb4ab';
                            },
                            // Returns the Transaction string
                            label: function(context) {
                                if (pointRadii[context.dataIndex] === 0) return null; 
                                const idx = context.dataIndex;
                                const txAmt = txAmounts[idx]; 
                                const creditStatus = isCredit[idx];
                                const sign = creditStatus ? '+' : '-';
                                return `Tx: ${sign}₹${txAmt.toLocaleString('en-IN', {maximumFractionDigits: 0})}`;
                            },
                            // Returns the Balance string in the footer (inherits footerColor)
                            footer: function(tooltipItems) {
                                const item = tooltipItems[0];
                                if (!item || pointRadii[item.dataIndex] === 0) return null;
                                return `Balance: ₹${item.parsed.y.toLocaleString('en-IN', {maximumFractionDigits: 0})}`;
                            }
                        }
                    }
                },
                scales: {
                    x: { display: false },
                    y: { 
                        display: true, 
                        min: 0,
                        border: { display: false },
                        ticks: { display: false },
                        grid: { 
                            color: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)',
                            drawTicks: false,
                            borderDash: [4, 4]
                        }
                    }
                },
                layout: {
                    padding: { top: 10, bottom: -10, left: -10, right: -10 } 
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
        
        const wrapper = barCtx.parentElement.parentElement;
        if(wrapper) {
            setTimeout(() => { wrapper.scrollLeft = wrapper.scrollWidth; }, 100);
        }
    }
}

// ==========================================
// SALARY PLANNER
// ==========================================
async function loadPlanner() {
    const prof = await fetchAPI('/profile');
    if (prof.res.ok) {
        const planTakeHome = document.getElementById('planTakeHome');
        const planEss = document.getElementById('planEssentials');
        const planDebt = document.getElementById('planDebts');
        if (planTakeHome) planTakeHome.value = prof.data.take_home_salary || 0;
        if (planEss) planEss.value = prof.data.essential_expenses || 0;
        if (planDebt) planDebt.value = prof.data.debt_obligations || 0;
    }
    
    const { res, data } = await fetchAPI('/plan');
    if (res.ok) {
        const div = document.getElementById('plannerResult');
        if (!div) return;
        if (data.status === 'deficit') {
            div.innerHTML = `<div class="glass-panel p-5 rounded-2xl border-l-4 border-l-error text-error font-bold">Deficit: Your obligations exceed take-home pay by ₹${parseFloat(data.shortfall).toLocaleString('en-IN')}</div>`;
        } else {
            div.innerHTML = `
                <div class="glass-panel p-5 rounded-2xl border-t-2 border-t-tertiary">
                    <div class="flex items-center justify-between mb-3">
                        <span class="font-label-caps text-[11px] uppercase text-tertiary font-bold tracking-wider">Emergency Fund</span>
                        <span class="px-2 py-0.5 rounded text-[11px] bg-tertiary/10 text-tertiary font-bold">10% Target</span>
                    </div>
                    <p class="font-metric-xl text-3xl font-bold currency-figure text-on-surface">₹${parseFloat(data.emergency_target).toLocaleString('en-IN')}</p>
                </div>
                <div class="glass-panel p-5 rounded-2xl border-t-2 border-t-secondary">
                    <div class="flex items-center justify-between mb-3">
                        <span class="font-label-caps text-[11px] uppercase text-secondary font-bold tracking-wider">Short-Term Goals</span>
                        <span class="px-2 py-0.5 rounded text-[11px] bg-secondary/10 text-secondary font-bold">10% Target</span>
                    </div>
                    <p class="font-metric-xl text-3xl font-bold currency-figure text-on-surface">₹${parseFloat(data.short_term_target).toLocaleString('en-IN')}</p>
                </div>
                <div class="glass-panel p-5 rounded-2xl border-t-2 border-t-primary-container">
                    <div class="flex items-center justify-between mb-3">
                        <span class="font-label-caps text-[11px] uppercase text-primary font-bold tracking-wider">Investments</span>
                        <span class="px-2 py-0.5 rounded text-[11px] bg-primary/10 text-primary font-bold">10% Target</span>
                    </div>
                    <p class="font-metric-xl text-3xl font-bold currency-figure text-on-surface">₹${parseFloat(data.investments_target).toLocaleString('en-IN')}</p>
                </div>
                <div class="glass-panel p-5 rounded-2xl border-t-2 border-t-outline-variant">
                    <div class="flex items-center justify-between mb-3">
                        <span class="font-label-caps text-[11px] uppercase text-on-surface-variant font-bold tracking-wider">Discretionary</span>
                        <span class="px-2 py-0.5 rounded text-[11px] bg-surface-variant text-on-surface-variant font-bold">Residual</span>
                    </div>
                    <p class="font-metric-xl text-3xl font-bold currency-figure text-on-surface">₹${parseFloat(data.discretionary_allowance).toLocaleString('en-IN')}</p>
                </div>
            `;
        }
    }
}

// ==========================================
// MONTH CLOSURE & ALLOCATION
// ==========================================
let globalMonthForClosure = "";

async function loadClosure() {
    const d = new Date();
    globalMonthForClosure = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    
    const { res, data } = await fetchAPI(`/closure/${globalMonthForClosure}`);
    if (!res.ok) return;

    const lbl = document.getElementById('closeMonthLabel');
    if (lbl) lbl.innerText = `Reconciliation for ${globalMonthForClosure}`;
    
    const clInc = document.getElementById('clRecordedIncome');
    if (clInc) clInc.innerText = `₹${parseFloat(data.recorded_income || 0).toLocaleString('en-IN')}`;
    
    const clExp = document.getElementById('clRecordedExpense');
    if (clExp) clExp.innerText = `₹${parseFloat(data.recorded_expense || 0).toLocaleString('en-IN')}`;
    
    const surplusEl = document.getElementById('clRecordedSurplus');
    if (surplusEl) surplusEl.innerText = `₹${parseFloat(data.recorded_surplus || 0).toLocaleString('en-IN')}`;
    
    const clAction = document.getElementById('closureAction');
    const allocSection = document.getElementById('allocationSection');
    if (!clAction || !allocSection) return;

    clAction.dataset.recordedSurplus = data.recorded_surplus;

    if (data.is_closed) {
        clAction.innerHTML = `
            <div class="p-5 rounded-2xl bg-tertiary/10 border border-tertiary/30 transition-all flex items-start gap-4">
                <div class="w-10 h-10 rounded-xl bg-tertiary/20 text-tertiary flex items-center justify-center flex-shrink-0">
                    <span class="material-symbols-outlined text-2xl">check_circle</span>
                </div>
                <div>
                    <h4 class="font-headline-sm text-lg font-bold text-tertiary">Ledger Sealed</h4>
                    <p class="font-body-sm text-sm text-on-surface-variant mt-1">Month closed with a confirmed physical bank surplus of ₹${parseFloat(data.confirmed_surplus||0).toLocaleString('en-IN')}</p>
                </div>
            </div>`;
        allocSection.style.display = 'block';
        allocSection.dataset.closureId = data.id;
    } else {
        clAction.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
                <div>
                    <label class="block font-label-caps text-[11px] font-bold uppercase text-outline mb-2">Actual Available Bank Balance (₹)</label>
                    <div class="relative">
                        <span class="absolute left-3.5 top-1/2 -translate-y-1/2 text-on-surface-variant font-bold text-base">₹</span>
                        <input id="physical-balance-input" oninput="checkDiscrepancy()" type="number" class="w-full bg-surface-container/60 text-on-surface pl-8 pr-4 py-3 rounded-xl border border-outline-variant/30 font-mono font-bold focus:border-secondary focus:ring-1 focus:ring-secondary/40 outline-none text-lg">
                    </div>
                </div>
                <div id="discrepancy-card" class="p-5 rounded-2xl bg-surface-container/60 border border-outline-variant/30 transition-all flex items-start gap-4">
                    <div class="w-10 h-10 rounded-xl bg-surface-variant text-outline flex items-center justify-center flex-shrink-0">
                        <span id="discrepancy-icon" class="material-symbols-outlined text-2xl">sync</span>
                    </div>
                    <div>
                        <h4 id="discrepancy-title" class="font-headline-sm text-sm font-bold text-on-surface">Enter Balance</h4>
                        <p id="discrepancy-desc" class="font-body-sm text-xs text-on-surface-variant mt-1">To reconcile variance.</p>
                        <p id="discrepancy-diff" class="font-mono text-xs font-bold mt-2 hidden"></p>
                    </div>
                </div>
            </div>
            <div class="pt-4 border-t border-outline-variant/20 flex justify-end mt-6">
                <button onclick="document.getElementById('closure-modal').classList.remove('hidden'); document.getElementById('closure-modal').classList.add('flex');" class="px-6 py-3 rounded-xl bg-primary-container text-white font-bold shadow-lg hover:brightness-110 transition-all flex items-center gap-2">
                    <span class="material-symbols-outlined">check_circle</span> Confirm & Close Month
                </button>
            </div>`;
        allocSection.style.display = 'none';
    }
}

function checkDiscrepancy() {
    const recorded = parseFloat(document.getElementById('closureAction').dataset.recordedSurplus) || 0;
    const inputField = document.getElementById('physical-balance-input');
    const physicalInput = parseFloat(inputField ? inputField.value : 0);
    
    const card = document.getElementById('discrepancy-card');
    const icon = document.getElementById('discrepancy-icon');
    const title = document.getElementById('discrepancy-title');
    const desc = document.getElementById('discrepancy-desc');
    const diff = document.getElementById('discrepancy-diff');
    
    const modalSurplus = document.getElementById('modal-conf-surplus');
    if (modalSurplus) modalSurplus.innerText = isNaN(physicalInput) ? '₹0' : `₹${physicalInput.toLocaleString('en-IN')}`;

    if (isNaN(physicalInput)) {
        if(card) card.className = 'p-5 rounded-2xl bg-surface-container/60 border border-outline-variant/30 transition-all flex items-start gap-4';
        if(icon) { icon.innerText = 'sync'; icon.className = 'material-symbols-outlined text-2xl text-outline'; }
        if(title) { title.className = 'font-headline-sm text-sm font-bold text-on-surface'; title.innerText = 'Enter Balance'; }
        if(desc) desc.innerText = 'To reconcile variance.'; 
        if(diff) diff.classList.add('hidden');
        return;
    }

    if(diff) diff.classList.remove('hidden');
    const variance = physicalInput - recorded;

    if (variance === 0) {
        if(card) card.className = 'p-5 rounded-2xl bg-tertiary/10 border border-tertiary/30 transition-all flex items-start gap-4';
        if(icon) { icon.innerText = 'check_circle'; icon.className = 'material-symbols-outlined text-2xl text-tertiary'; }
        if(title) { title.className = 'font-headline-sm text-sm font-bold text-tertiary'; title.innerText = 'Zero Variance / Fully Reconciled'; }
        if(desc) desc.innerText = 'Ledger exactly matches physical vault assets.';
        if(diff) { diff.className = 'font-mono text-xs font-bold text-tertiary mt-2'; diff.innerText = 'Variance: ₹0.00'; }
    } else if (variance < 0) {
        if(card) card.className = 'p-5 rounded-2xl bg-error/10 border border-error/30 transition-all flex items-start gap-4';
        if(icon) { icon.innerText = 'warning'; icon.className = 'material-symbols-outlined text-2xl text-error'; }
        if(title) { title.className = 'font-headline-sm text-sm font-bold text-error'; title.innerText = 'Deficit Detected'; }
        if(desc) desc.innerText = `Bank is lower than calculated surplus.`;
        if(diff) { diff.className = 'font-mono text-xs font-bold text-error mt-2'; diff.innerText = 'Variance: -₹' + Math.abs(variance).toLocaleString('en-IN'); }
    } else {
        if(card) card.className = 'p-5 rounded-2xl bg-secondary/10 border border-secondary/30 transition-all flex items-start gap-4';
        if(icon) { icon.innerText = 'info'; icon.className = 'material-symbols-outlined text-2xl text-secondary'; }
        if(title) { title.className = 'font-headline-sm text-sm font-bold text-secondary'; title.innerText = 'Surplus Excess'; }
        if(desc) desc.innerText = `Vault has excess over ledger bookings.`;
        if(diff) { diff.className = 'font-mono text-xs font-bold text-secondary mt-2'; diff.innerText = 'Variance: +₹' + variance.toLocaleString('en-IN'); }
    }
}

async function executeConfirmMonthClosure() {
    const inputField = document.getElementById('physical-balance-input');
    const actual = inputField ? inputField.value : 0;
    const modal = document.getElementById('closure-modal');
    if (modal) {
        modal.classList.remove('flex');
        modal.classList.add('hidden');
    }
    
    const { res, data } = await fetchAPI(`/closure/${globalMonthForClosure}/confirm`, {
        method: 'POST', body: JSON.stringify({ confirmed_surplus: actual })
    });
    if (res.ok) {
        showPopup("Month sealed successfully", "success");
        loadClosure();
    } else {
        showPopup(data.error, "error");
    }
}

async function allocateSurplus() {
    const allocSection = document.getElementById('allocationSection');
    const closureId = allocSection ? allocSection.dataset.closureId : null;
    if (!closureId) return;

    const { res, data } = await fetchAPI(`/closure/${closureId}/allocate`, {
        method: 'POST',
        body: JSON.stringify({
            emergency: document.getElementById('allocEmergency').value,
            short_term: document.getElementById('allocShortTerm').value,
            investments: document.getElementById('allocInvestments').value
        })
    });
    if (res.ok) { showPopup("Allocated successfully!", "success"); loadClosure(); }
    else showPopup(data.error, "error");
}

// ==========================================
// AI ASSISTANT
// ==========================================
let aiBusy = false;
async function askAI(promptText = null) {
    if (aiBusy) return;
    const input = document.getElementById('aiInput');
    const msg = (promptText || input.value).trim();
    if (!msg) return;

    const chatBox = document.getElementById('aiChatBox');
    if (!chatBox) return;
    
    chatBox.innerHTML += `
        <div class="flex gap-3 max-w-2xl ml-auto justify-end">
            <div class="space-y-2 text-right">
                <div class="p-4 rounded-2xl bg-primary-container text-white font-medium text-sm text-left shadow-md">${escapeHTML(msg)}</div>
                <span class="text-[10px] text-outline pr-1 font-mono">Just now • Verified User</span>
            </div>
            <div class="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center font-bold text-on-primary text-xs flex-shrink-0">US</div>
        </div>`;
    if (!promptText && input) input.value = "";
    chatBox.scrollTop = chatBox.scrollHeight;
    aiBusy = true;

    const loadId = 'load-' + Date.now();
    chatBox.innerHTML += `
        <div id="${loadId}" class="flex gap-3 max-w-3xl">
            <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-secondary to-primary-container flex items-center justify-center text-white flex-shrink-0 shadow-md shadow-secondary/20"><span class="material-symbols-outlined text-sm">smart_toy</span></div>
            <div class="p-4 rounded-2xl bg-surface-container/80 text-outline text-sm">Processing node telemetry...</div>
        </div>`;
    chatBox.scrollTop = chatBox.scrollHeight;

    const { res, data } = await fetchAPI('/ai/chat', { method: 'POST', body: JSON.stringify({ message: msg }) });
    const loader = document.getElementById(loadId);
    if (loader) loader.remove();

    if (res.ok && data.answer) {
        let safeHTML = escapeHTML(data.answer).replace(/\*\*(.*?)\*\*/g, '<strong class="text-secondary">$1</strong>').replace(/\n/g, '<br>');
        chatBox.innerHTML += `
            <div class="flex gap-3 max-w-3xl">
                <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-secondary to-primary-container flex items-center justify-center text-white font-bold flex-shrink-0 shadow-md shadow-secondary/20"><span class="material-symbols-outlined text-sm">smart_toy</span></div>
                <div class="space-y-2">
                    <div class="p-4 rounded-2xl bg-surface-container/80 dark:bg-surface-container-high/60 border border-outline-variant/30 text-sm text-on-surface leading-relaxed">
                        <p class="font-bold text-secondary text-sm mb-1">FinTrack AI Financial Intelligence</p>
                        ${safeHTML}
                    </div>
                    <span class="text-[10px] text-outline pl-1 font-mono">Just now • Copilot Node Active</span>
                </div>
            </div>`;
    } else {
        chatBox.innerHTML += `
            <div class="flex gap-3 max-w-3xl">
                <div class="w-8 h-8 rounded-xl bg-error/80 flex items-center justify-center text-white"><span class="material-symbols-outlined text-sm">error</span></div>
                <div class="p-4 rounded-2xl bg-error/10 text-error border border-error/30 text-sm">${escapeHTML(data.error || 'Failed')}</div>
            </div>`;
    }
    chatBox.scrollTop = chatBox.scrollHeight;
    aiBusy = false;
}

function clearChatFeed() {
    const chatBox = document.getElementById('aiChatBox');
    if (chatBox) {
        chatBox.innerHTML = `
            <div class="flex gap-3 max-w-3xl">
                <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-secondary to-primary-container flex items-center justify-center text-white font-bold flex-shrink-0 shadow-md shadow-secondary/20">
                    <span class="material-symbols-outlined text-base">smart_toy</span>
                </div>
                <div class="space-y-2">
                    <div class="p-4 rounded-2xl bg-surface-container/80 dark:bg-surface-container-high/60 border border-outline-variant/30 text-sm text-on-surface leading-relaxed">
                        <p class="font-bold text-secondary text-sm mb-1">Session Reset</p>
                        <p>AI session memory cleared. Ready for new tax, budget, or investment telemetry queries.</p>
                    </div>
                </div>
            </div>`;
    }
}

// ==========================================
// PRODUCTS
// ==========================================
async function loadProducts() {
    const { res, data } = await fetchAPI('/products');
    if (!res.ok || !Array.isArray(data)) return;

    const list = document.getElementById('productsList');
    if (!list) return;

    let html = "";
    if (data.length > 0) {
        const surplus = parseFloat(data[0].user_surplus) || 0;
        html += `
        <div class="glass-panel p-5 rounded-2xl border-l-4 border-l-secondary flex flex-col md:flex-row md:items-center justify-between gap-4" style="grid-column: 1 / -1;">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-secondary/15 text-secondary flex items-center justify-center flex-shrink-0"><span class="material-symbols-outlined text-2xl">account_balance</span></div>
                <div>
                    <h3 class="text-lg font-bold text-on-surface">Surplus Headroom Assessment</h3>
                    <p class="text-sm text-on-surface-variant">Your recorded surplus is <strong class="currency-figure text-secondary font-bold">₹${surplus.toLocaleString('en-IN')}</strong>.</p>
                </div>
            </div>
            <button onclick="switchTab('month-closure')" class="px-4 py-2 rounded-xl bg-surface-container-high hover:bg-surface-variant text-on-surface text-xs font-semibold border border-outline-variant/30 transition-all flex items-center gap-1.5 self-start md:self-auto">
                <span>Go to Month Closure</span><span class="material-symbols-outlined text-sm">arrow_forward</span>
            </button>
        </div>`;
    }

    data.forEach(p => {
        const affordColor = p.is_affordable ? 'text-tertiary' : 'text-error';
        const affordBg = p.is_affordable ? 'bg-tertiary/10 border-tertiary/30' : 'bg-error/10 border-error/30';
        const affordText = p.is_affordable ? 'Affordable' : 'Requires More Savings';
        const riskColor = p.risk_level.toLowerCase().includes('high') ? 'text-error' : 'text-tertiary';
        const estLine = p.estimated_1yr_return
            ? `<div class="col-span-2 p-2.5 rounded-xl bg-surface-container/60 border border-outline-variant/20">
                <span class="text-outline block text-[10px] uppercase">1-Yr Est. on ₹${parseFloat(p.estimate_principal).toLocaleString('en-IN')}</span>
                <span class="font-semibold text-secondary">+₹${parseFloat(p.estimated_1yr_return).toLocaleString('en-IN')} (${escapeHTML(p.interest_rate_pct)}%)</span>
               </div>` : '';

        html += `
            <div class="glass-panel p-6 rounded-2xl liquid-border hover:border-secondary/40 transition-all flex flex-col justify-between opacity-${p.is_affordable ? '100' : '65'}">
                <div>
                    <div class="flex items-start justify-between gap-2 mb-3">
                        <div>
                            <span class="font-label-caps text-[11px] uppercase text-outline">${escapeHTML(p.category)}</span>
                            <h3 class="text-lg font-bold text-on-surface mt-0.5">${escapeHTML(p.name)}</h3>
                        </div>
                        <span class="px-2.5 py-1 rounded-full ${affordBg} ${affordColor} text-xs font-bold border">${affordText}</span>
                    </div>
                    <div class="grid grid-cols-2 gap-3 text-xs mb-4">
                        <div class="p-2.5 rounded-xl bg-surface-container/60 border border-outline-variant/20">
                            <span class="text-outline block text-[10px] uppercase">Risk Level</span>
                            <span class="font-semibold ${riskColor}">${escapeHTML(p.risk_level)}</span>
                        </div>
                        <div class="p-2.5 rounded-xl bg-surface-container/60 border border-outline-variant/20">
                            <span class="text-outline block text-[10px] uppercase">Liquidity / Lock-in</span>
                            <span class="font-semibold text-on-surface">${escapeHTML(p.lock_in_period || p.liquidity)}</span>
                        </div>
                        <div class="p-2.5 rounded-xl bg-surface-container/60 border border-outline-variant/20">
                            <span class="text-outline block text-[10px] uppercase">Min Investment</span>
                            <span class="currency-figure font-semibold text-on-surface">₹${parseFloat(p.min_investment).toLocaleString('en-IN')}</span>
                        </div>
                        ${estLine}
                    </div>
                </div>
                <div class="flex items-center justify-between pt-3 border-t border-outline-variant/20 text-[11px] text-outline flex justify-between">
                    <a href="${escapeHTML(p.source_url)}" target="_blank" rel="noopener noreferrer" class="text-xs text-secondary font-bold hover:underline">Official Source</a>
                    <span>Verified: ${escapeHTML(p.verified_date)}</span>
                </div>
            </div>`;
    });
    list.innerHTML = html;
}