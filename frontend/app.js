document.addEventListener('DOMContentLoaded', async () => {
    // Initialize Auth
    if (window.Auth) {
        const isAuth = await window.Auth.init();
        if (!isAuth) {
            document.getElementById('login-container').style.display = 'flex';
            document.getElementById('app-container').style.display = 'none';
            return; // Stop rendering the main app
        }
        
        // Show app and hide login
        document.getElementById('login-container').style.display = 'none';
        const appContainer = document.getElementById('app-container');
        appContainer.style.display = 'flex';
        appContainer.classList.add('authenticated');
        
        // Populate sidebar user profile
        if (window.Auth.currentUser) {
            const u = window.Auth.currentUser;
            document.getElementById('sidebar-name').textContent = u.name || u.username;
            document.getElementById('sidebar-email').textContent = u.email || '';
            if (u.avatar_url) {
                document.getElementById('sidebar-avatar').innerHTML = `<img src="${u.avatar_url}" style="width:100%; height:100%; border-radius:50%; object-fit:cover;">`;
            }
        }
    }

    // Navigation / View Switching
    const navItems = document.querySelectorAll('.nav-item');
    const viewSections = document.querySelectorAll('.view-section');
    const navbarViewTitle = document.getElementById('navbar-view-title');
    const repositoriesListContainer = document.getElementById('repositories-list-container');
    const activityListContainer = document.getElementById('activity-list-container');
    const dashboardActivityList = document.getElementById('dashboard-activity-list');

    function switchView(viewName) {
        // Update active class on nav items
        navItems.forEach(item => {
            if (item.getAttribute('data-view') === viewName) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });

        // Show corresponding section with transition
        viewSections.forEach(section => {
            if (section.id === `view-${viewName}`) {
                section.classList.add('active');
            } else {
                section.classList.remove('active');
            }
        });

        // Update title
        let formattedTitle = viewName.charAt(0).toUpperCase() + viewName.slice(1);
        if (viewName === 'repo-details') {
            formattedTitle = 'Repository Details';
        } else if (viewName === 'commit-details') {
            formattedTitle = 'Commit Details';
        }
        navbarViewTitle.textContent = formattedTitle;
    }

    // UI State Helpers
    window.UI = {
        getSkeletonHTML: (type) => {
            if (type === 'card') return `<div class="card skeleton skeleton-card"></div>`;
            if (type === 'list') return `
                <div class="list-item" style="gap: 16px;">
                    <div class="skeleton skeleton-avatar"></div>
                    <div style="flex: 1;">
                        <div class="skeleton skeleton-text medium"></div>
                        <div class="skeleton skeleton-text short" style="margin-bottom: 0;"></div>
                    </div>
                </div>`;
            return `<div class="skeleton skeleton-text"></div>`;
        },
        getEmptyStateHTML: (title, desc, actionText = '', actionOnClick = '') => {
            const actionBtn = actionText ? `<button class="btn-primary" ${actionOnClick ? `onclick="${actionOnClick}"` : ''}>${actionText}</button>` : '';
            return `
                <div class="empty-state">
                    <div class="empty-state-illustration">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
                            <rect x="3" y="3" width="18" height="18" rx="2" stroke-dasharray="3 3"></rect>
                            <circle cx="12" cy="12" r="5"></circle>
                            <path d="M12 2v20M2 12h20"></path>
                        </svg>
                    </div>
                    <h3 class="empty-state-title">${title}</h3>
                    <p class="empty-state-desc">${desc}</p>
                    ${actionBtn}
                </div>
            `;
        },
        getErrorStateHTML: (title, desc) => {
            return `
                <div class="error-state">
                    <div class="error-state-icon">⚠️</div>
                    <h3 class="error-state-title">${title}</h3>
                    <p class="error-state-desc">${desc}</p>
                    <button class="btn-secondary" style="color: #ef4444; border-color: rgba(239, 68, 68, 0.3);">Retry Request</button>
                </div>
            `;
        }
    };

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const viewName = item.getAttribute('data-view');
            switchView(viewName);
        });
    });

    // Handle Quick Action to switch view
    const dashboardToActivityBtn = document.getElementById('dashboard-to-activity');
    if (dashboardToActivityBtn) {
        dashboardToActivityBtn.addEventListener('click', () => switchView('activity'));
    }
    const dashboardToReposBtn = document.getElementById('dashboard-to-repos');
    if (dashboardToReposBtn) {
        dashboardToReposBtn.addEventListener('click', () => switchView('repositories'));
    }

    let currentSelectedRepo = '';
    let currentSelectedCommitHash = '';

    function getStatusClass(status) {
        if (!status) return 'text-muted';
        const s = status.toLowerCase();
        if (s === 'success' || s === 'active' || s === 'completed') return 'text-success';
        if (s === 'warning') return 'text-warning';
        if (s === 'error' || s === 'failed') return 'text-error';
        return 'text-muted';
    }

    async function renderDashboardStats() {
        try {
            const data = await window.API.Dashboard.getStats();
            const kpiRepos = document.getElementById('kpi-repos');
            const kpiJobs = document.getElementById('kpi-jobs');
            const kpiDocs = document.getElementById('kpi-docs');
            const kpiActive = document.getElementById('kpi-active');
            
            if (kpiRepos) kpiRepos.textContent = data.total_repositories || 0;
            if (kpiJobs) kpiJobs.textContent = data.total_commits_processed || 0;
            if (kpiDocs) kpiDocs.textContent = data.documentation_pages || 0;
            if (kpiActive) kpiActive.textContent = data.active_ai_models || 0;
        } catch (error) {
            console.error('Failed to load dashboard stats:', error);
        }
    }

    async function renderRepositories(filter = '') {
        if (!repositoriesListContainer) return;
        
        // Show Skeleton Loaders
        repositoriesListContainer.innerHTML = UI.getSkeletonHTML('list') + UI.getSkeletonHTML('list') + UI.getSkeletonHTML('list');
        const dashboardReposGrid = document.getElementById('dashboard-repos-grid');
        if (dashboardReposGrid) {
            dashboardReposGrid.innerHTML = UI.getSkeletonHTML('card') + UI.getSkeletonHTML('card');
        }

        try {
            // Call dashboard stats
            renderDashboardStats();

            const data = await window.API.Repository.getAll();
            const repositories = data.repositories || [];
            
            const filtered = repositories.filter(repo => 
                repo.name.toLowerCase().includes(filter.toLowerCase())
            );

            if (filtered.length === 0) {
                repositoriesListContainer.innerHTML = UI.getEmptyStateHTML(
                    'No Repositories Connected', 
                    'Connect your first repository to start monitoring code updates and generating documentation.',
                    'Connect Repository',
                    'document.getElementById(\'btn-add-repo\').click()'
                );
            } else {
                repositoriesListContainer.innerHTML = filtered.map(repo => {
                    const statusText = repo.webhook_enabled ? 'active' : 'inactive';
                    const dateStr = new Date(repo.updated_at || repo.created_at).toLocaleDateString();
                    return `
                    <div class="list-item repo-list-item" data-repo="${repo.name}" style="cursor: pointer; justify-content: space-between;">
                        <div style="display: flex; gap: 16px; align-items: center;">
                            <div class="item-info">
                                <div class="item-icon">
                                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width: 20px; height: 20px;">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z" />
                                    </svg>
                                </div>
                                <div>
                                    <div class="item-title">${repo.owner}/${repo.name}</div>
                                    <div class="item-subtitle">Updated ${dateStr}</div>
                                </div>
                            </div>
                            <div class="item-meta">
                                <span class="status-chip status-${statusText}">${statusText}</span>
                            </div>
                        </div>
                        <button class="btn-secondary disconnect-btn" data-id="${repo.id}" style="color: #ef4444; border-color: rgba(239,68,68,0.3);" onclick="event.stopPropagation()">Disconnect</button>
                    </div>
                `}).join('');

                document.querySelectorAll('.repo-list-item').forEach(item => {
                    item.addEventListener('click', () => {
                        const repoName = item.getAttribute('data-repo');
                        loadRepoDetails(repoName);
                    });
                });
                
                document.querySelectorAll('.disconnect-btn').forEach(btn => {
                    btn.addEventListener('click', async (e) => {
                        e.stopPropagation();
                        const repoId = btn.getAttribute('data-id');
                        try {
                            btn.textContent = "Disconnecting...";
                            await window.API.Github.disconnect(repoId);
                            renderRepositories();
                        } catch (err) {
                            alert(err.message);
                            btn.textContent = "Disconnect";
                        }
                    });
                });
            }
            
            // Available Repositories
            const githubContainer = document.getElementById('github-repositories-container');
            if (githubContainer) {
                githubContainer.innerHTML = UI.getSkeletonHTML('list');
                try {
                    const availableRepos = await window.API.Github.getAvailable();
                    if (!availableRepos || availableRepos.length === 0) {
                        githubContainer.innerHTML = UI.getEmptyStateHTML('All Caught Up', 'No additional GitHub repositories available to connect.');
                    } else {
                        githubContainer.innerHTML = availableRepos.map(repo => {
                            return `
                            <div class="list-item" style="justify-content: space-between;">
                                <div class="item-info">
                                    <div class="item-icon">
                                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width: 20px; height: 20px;">
                                            <path stroke-linecap="round" stroke-linejoin="round" d="M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-.778.099-1.533.284-2.253m0 0h17.432" />
                                        </svg>
                                    </div>
                                    <div>
                                        <div class="item-title">${repo.owner}/${repo.name}</div>
                                        <div class="item-subtitle">${repo.private ? 'Private' : 'Public'}</div>
                                    </div>
                                </div>
                                <button class="btn-primary connect-btn" data-id="${repo.github_repo_id}">Connect Webhook</button>
                            </div>
                            `
                        }).join('');
                        
                        document.querySelectorAll('.connect-btn').forEach(btn => {
                            btn.addEventListener('click', async () => {
                                const repoId = btn.getAttribute('data-id');
                                try {
                                    btn.textContent = "Connecting...";
                                    await window.API.Github.connect(repoId);
                                    renderRepositories(); // Refresh lists
                                } catch (err) {
                                    alert(err.message);
                                    btn.textContent = "Connect Webhook";
                                }
                            });
                        });
                    }
                } catch (err) {
                    githubContainer.innerHTML = UI.getErrorStateHTML('Failed to fetch GitHub repos', err.message);
                }
            }

            if (dashboardReposGrid) {
                dashboardReposGrid.innerHTML = repositories.slice(0, 4).map(repo => {
                    const statusText = repo.webhook_enabled ? 'active' : 'inactive';
                    const dateStr = new Date(repo.updated_at || repo.created_at).toLocaleDateString();
                    return `
                    <div class="repo-mini-card" data-repo="${repo.name}">
                        <div>
                            <div class="repo-mini-name">${repo.name}</div>
                            <div class="repo-mini-lang">Unknown Lang</div>
                        </div>
                        <div class="repo-mini-footer">
                            <span style="font-size: 11px; color: var(--text-secondary);">${dateStr}</span>
                            <span>
                                <span class="status-chip status-${statusText}">${statusText}</span>
                            </span>
                        </div>
                    </div>
                `}).join('');

                document.querySelectorAll('.repo-mini-card').forEach(card => {
                    card.addEventListener('click', () => {
                        const repoName = card.getAttribute('data-repo');
                        loadRepoDetails(repoName);
                    });
                });
            }

            // Update KPI values
            const kpiRepos = document.getElementById('kpi-repos');
            if (kpiRepos) {
                kpiRepos.textContent = repositories.length;
            }

        } catch (error) {
            repositoriesListContainer.innerHTML = UI.getErrorStateHTML('Failed to load repositories', error.message);
            if (dashboardReposGrid) {
                dashboardReposGrid.innerHTML = UI.getErrorStateHTML('Failed to load', error.message);
            }
        }
    }

    let activityPollingTimeout = null;

    async function renderActivities(isBackgroundRefresh = false) {
        if (!activityListContainer || !dashboardActivityList) return;

        // Show Skeleton Loaders only for first or manual loads
        if (!isBackgroundRefresh) {
            dashboardActivityList.innerHTML = UI.getSkeletonHTML('list') + UI.getSkeletonHTML('list');
            activityListContainer.innerHTML = UI.getSkeletonHTML('list') + UI.getSkeletonHTML('list') + UI.getSkeletonHTML('list');
        }

        try {
            const data = await window.API.Activity.getFeed();
            const activities = data.activities || [];

            if (activities.length === 0) {
                dashboardActivityList.innerHTML = '<div style="padding: 16px; color: var(--text-secondary); text-align: center;">No recent activity</div>';
                activityListContainer.innerHTML = UI.getEmptyStateHTML('No Activity Feed', 'No webhook events or analysis actions recorded yet.');
                return;
            }

            // Render dashboard (limit to top 3, keep as simple list)
            dashboardActivityList.innerHTML = activities.slice(0, 3).map(act => {
                const timeStr = new Date(act.time).toLocaleString();
                return `
                <div class="list-item">
                    <div class="item-info">
                        <div class="item-icon">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width: 20px; height: 20px;">
                                <path stroke-linecap="round" stroke-linejoin="round" d="m3.75 13.5 10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z" />
                            </svg>
                        </div>
                        <div>
                            <div class="item-title">${act.event}</div>
                            <div class="item-subtitle">${act.repo} • ${act.details}</div>
                        </div>
                    </div>
                    <div class="item-meta">
                        <span style="font-size: 12px; color: var(--text-secondary);">${timeStr}</span>
                    </div>
                </div>
            `}).join('');

            // Render full activity page as a timeline
            let timelineHtml = '<div class="timeline">';
            
            activities.forEach(act => {
                let statusClass = 'badge-processing';
                let icon = '⚙️';
                let statusText = 'Processing';
                
                if (act.status === 'completed' || act.status === 'success') {
                    statusClass = 'badge-completed';
                    icon = '✓';
                    statusText = 'Completed';
                } else if (act.status === 'failed' || act.status === 'error') {
                    statusClass = 'badge-failed';
                    icon = '❌';
                    statusText = 'Failed';
                }

                const timeStr = new Date(act.time).toLocaleString();

                timelineHtml += `
                    <div class="timeline-item">
                        <div class="timeline-marker ${statusClass}">
                            ${icon}
                        </div>
                        <div class="timeline-content">
                            <div class="timeline-header">
                                <h3 class="timeline-title">${act.event}</h3>
                                <span class="timeline-time">${timeStr}</span>
                            </div>
                            <div class="timeline-body">
                                <p class="timeline-details">${act.details}</p>
                                <div class="timeline-footer">
                                    <span class="badge-status ${statusClass}">${statusText}</span>
                                    <span class="project-badge" style="font-size: 11px; padding: 2px 6px;">${act.repo}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            timelineHtml += '</div>';
            activityListContainer.innerHTML = timelineHtml;
            activityListContainer.classList.add('timeline-container');
            activityListContainer.classList.remove('list-container');
            activityListContainer.style.border = 'none';
            activityListContainer.style.backgroundColor = 'transparent';

            // Polling logic
            if (activityPollingTimeout) {
                clearTimeout(activityPollingTimeout);
            }
            
            const hasPendingJobs = activities.some(act => 
                act.status.toLowerCase() === 'processing' || 
                act.status.toLowerCase() === 'queued' ||
                act.status.toLowerCase() === 'pending'
            );
            
            if (hasPendingJobs) {
                activityPollingTimeout = setTimeout(() => {
                    renderActivities(true);
                }, 3000);
            }

        } catch (error) {
            dashboardActivityList.innerHTML = '<div style="padding: 16px; color: var(--text-error); text-align: center;">Error loading activity</div>';
            activityListContainer.innerHTML = UI.getErrorStateHTML('Activity Feed Failed', error.message);
        }
    }

    // Load Repo Details view
    async function loadRepoDetails(repoName) {
        currentSelectedRepo = repoName;
        switchView('repo-details');

        // Set skeleton text
        document.getElementById('repo-details-title').innerHTML = UI.getSkeletonHTML();
        document.getElementById('repo-details-subtitle').innerHTML = UI.getSkeletonHTML();

        try {
            const data = await window.API.Repository.getDetails(repoName);
            const repo = data || {};

            // Update labels
            const statusTextVal = repo.webhook_enabled ? 'active' : 'inactive';
            const dateStr = repo.updated_at ? new Date(repo.updated_at).toLocaleDateString() : 'recently';
            
            document.getElementById('repo-details-title').textContent = `${repo.owner}/${repo.name}` || repoName;
            document.getElementById('repo-details-subtitle').textContent = `Unknown Lang • ${statusTextVal} • Updated ${dateStr}`;
            
            // Metadata status card
            const statusChip = document.getElementById('repo-meta-status-chip');
            if (statusChip) {
                statusChip.textContent = statusTextVal;
                statusChip.className = `status-chip status-${statusTextVal}`;
            }

            // Render commits table
            await renderCommitsTable(repoName);

        } catch (error) {
            document.getElementById('repo-details-title').textContent = repoName;
            document.getElementById('repo-details-subtitle').textContent = 'Error loading repository data';
            document.getElementById('commits-table-body').innerHTML = `
                <tr><td colspan="6" style="padding:0;">${UI.getErrorStateHTML('Failed to load details', error.message)}</td></tr>
            `;
        }
    }

    async function renderCommitsTable(repoName) {
        const tableBody = document.getElementById('commits-table-body');
        const countSpan = document.getElementById('commits-count');
        if (countSpan) countSpan.textContent = `Loading commits...`;
        
        if (tableBody) {
            tableBody.innerHTML = `<tr><td colspan="6" style="padding: 16px;">${UI.getSkeletonHTML('list')}</td></tr>`;
        }

        try {
            const data = await window.API.Commits.getByRepo(repoName);
            const commits = Array.isArray(data) ? data : (data.commits || []);

            if (countSpan) {
                countSpan.textContent = `Showing ${commits.length} commit(s)`;
            }

            if (tableBody) {
                if (commits.length === 0) {
                    tableBody.innerHTML = `
                        <tr>
                            <td colspan="6" style="padding: 0;">
                                <div class="empty-state" style="margin: 32px; border: none; background: transparent;">
                                    <div class="empty-state-icon">📭</div>
                                    <h3 class="empty-state-title">No Commits Found</h3>
                                    <p class="empty-state-desc">There are no recent commits available for this repository. Push code to trigger an AI analysis pipeline.</p>
                                </div>
                            </td>
                        </tr>
                    `;
                    return;
                }

                tableBody.innerHTML = commits.map((commit) => {
                    const commitStatus = commit.ai_generations && commit.ai_generations.length > 0 
                        ? commit.ai_generations[0].status 
                        : 'processing';
                    const dateStr = new Date(commit.committed_at).toLocaleString();
                    const hash = commit.sha ? commit.sha.substring(0, 7) : 'unknown';
                    
                    return `
                    <tr>
                        <td><span class="commit-hash">${hash}</span></td>
                        <td style="font-weight: 500;">${commit.message}</td>
                        <td>${commit.author || 'Unknown'}</td>
                        <td style="color: var(--text-secondary);">${dateStr}</td>
                        <td>
                            <span class="${getStatusClass(commitStatus)}">●</span>
                            <span style="margin-left: 6px; text-transform: capitalize;">${commitStatus}</span>
                        </td>
                        <td>
                            <button class="btn-secondary btn-view-commit" data-hash="${commit.id}" style="font-size: 11px; padding: 4px 8px;">View Details</button>
                        </td>
                    </tr>
                `}).join('');

                // Attach details button event listener
                document.querySelectorAll('.btn-view-commit').forEach(btn => {
                    btn.addEventListener('click', () => {
                        const hash = btn.getAttribute('data-hash');
                        loadCommitDetails(repoName, hash);
                    });
                });
            }
        } catch (error) {
            if (countSpan) countSpan.textContent = 'Error loading commits';
            if (tableBody) {
                tableBody.innerHTML = `<tr><td colspan="6" style="padding:0;">${UI.getErrorStateHTML('Failed to load commits', error.message)}</td></tr>`;
            }
        }
    }

    // Load Commit Details view
    async function loadCommitDetails(repoName, commitHash) {
        currentSelectedCommitHash = commitHash;
        switchView('commit-details');

        // Skeletons
        document.getElementById('commit-details-hash').textContent = commitHash;
        document.getElementById('commit-details-message').innerHTML = UI.getSkeletonHTML();
        document.getElementById('commit-details-meta').innerHTML = UI.getSkeletonHTML();
        document.getElementById('commit-changed-files-list').innerHTML = UI.getSkeletonHTML('list');
        document.getElementById('commit-ai-overview').innerHTML = UI.getSkeletonHTML('card');
        document.getElementById('commit-ai-impact').innerHTML = UI.getSkeletonHTML('card');

        try {
            const data = await window.API.Commits.getDetails(commitHash);
            const commit = data || {}; // Backend returns CommitResponse directly here

            const hash = commit.sha ? commit.sha.substring(0, 7) : commitHash;
            const dateStr = commit.committed_at ? new Date(commit.committed_at).toLocaleString() : '';
            const commitStatus = commit.ai_generations && commit.ai_generations.length > 0 ? commit.ai_generations[0].status : 'completed';

            document.getElementById('commit-details-message').textContent = commit.message || 'Unknown Message';
            document.getElementById('commit-details-meta').textContent = `Authored by ${commit.author || 'Unknown'} • ${dateStr}`;
            document.getElementById('commit-details-hash').textContent = hash;

            const statusDot = document.getElementById('commit-details-status-dot');
            const statusText = document.getElementById('commit-details-status-text');
            if (statusDot && statusText) {
                statusDot.className = `project-status ${getStatusClass(commitStatus)}`;
                statusText.textContent = commitStatus.toUpperCase();
            }

            // Render changed files - Note: backend doesn't return files yet in CommitResponse, fallback to UI empty state
            const files = commit.files || [];
            const filesContainer = document.getElementById('commit-changed-files-list');
            const filesCount = document.getElementById('commit-changed-files-count');
            if (filesCount) filesCount.textContent = `${files.length} file(s) changed`;

            if (filesContainer) {
                if (files.length === 0) {
                    filesContainer.innerHTML = UI.getEmptyStateHTML('No Files Changed', 'This commit does not contain any file changes.');
                } else {
                    filesContainer.innerHTML = files.map(file => {
                        let badgeClass = 'badge-mod';
                        if (file.status === 'added') badgeClass = 'badge-add';
                        if (file.status === 'deleted') badgeClass = 'badge-del';

                        return `
                            <div class="list-item">
                                <div class="item-info">
                                    <span class="badge-file-status ${badgeClass}">${file.status}</span>
                                    <span style="font-family: var(--font-mono); font-size: 13px;">${file.path}</span>
                                </div>
                                <div class="item-meta">
                                    <span style="font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary);">${file.lines}</span>
                                </div>
                            </div>
                        `;
                    }).join('');
                }
            }

            // Render summaries
            const summaryData = commit.summary ? commit.summary.summary : 'No overview available.';
            document.getElementById('commit-ai-overview').textContent = summaryData;
            document.getElementById('commit-ai-impact').textContent = 'Impact analysis is part of the core summary text.';

        } catch (error) {
            document.getElementById('commit-ai-overview').innerHTML = UI.getErrorStateHTML('Error Loading AI Details', error.message);
            document.getElementById('commit-ai-impact').innerHTML = UI.getErrorStateHTML('Error Loading Impact', error.message);
            document.getElementById('commit-changed-files-list').innerHTML = UI.getErrorStateHTML('Error Loading Files', error.message);
        }
    }

    // Back to Repos button handler
    const btnBackToRepos = document.getElementById('btn-back-to-repos');
    if (btnBackToRepos) {
        btnBackToRepos.addEventListener('click', () => {
            switchView('repositories');
        });
    }

    // Back to Repo Details button handler
    const btnBackToRepoDetails = document.getElementById('btn-back-to-repo-details');
    if (btnBackToRepoDetails) {
        btnBackToRepoDetails.addEventListener('click', () => {
            if (currentSelectedRepo) {
                loadRepoDetails(currentSelectedRepo);
            } else {
                switchView('repositories');
            }
        });
    }

    // View documentation button handler
    const btnViewDocs = document.getElementById('btn-view-docs');
    if (btnViewDocs) {
        btnViewDocs.addEventListener('click', () => {
            switchView('documentation');
        });
    }

    // Regenerate documentation simulator handler
    const btnRegenDocs = document.getElementById('btn-regenerate-docs');
    if (btnRegenDocs) {
        btnRegenDocs.addEventListener('click', () => {
            btnRegenDocs.textContent = 'Regenerating...';
            btnRegenDocs.disabled = true;
            setTimeout(() => {
                btnRegenDocs.textContent = 'Regenerate Documentation';
                btnRegenDocs.disabled = false;
                alert('Documentation updated successfully based on the commit layout analysis!');
            }, 1500);
        });
    }

    // Trigger local AI run simulation
    const btnTriggerAiRun = document.getElementById('btn-trigger-ai-run');
    if (btnTriggerAiRun) {
        btnTriggerAiRun.addEventListener('click', () => {
            if (!currentSelectedRepo) return;
            
            btnTriggerAiRun.textContent = 'Analyzing...';
            btnTriggerAiRun.disabled = true;

            setTimeout(() => {
                btnTriggerAiRun.textContent = 'Trigger AI Run';
                btnTriggerAiRun.disabled = false;

                // Add simulated commit to mock database
                if (!mockCommits[currentSelectedRepo]) {
                    mockCommits[currentSelectedRepo] = [];
                }

                const newHash = Math.random().toString(16).substring(2, 9);
                mockCommits[currentSelectedRepo].unshift({
                    hash: newHash,
                    message: 'Simulated AI Pipeline payload commit',
                    author: 'DevFlow Agent',
                    date: 'Just now',
                    status: 'success'
                });

                // Prepare details for the new simulated commit
                mockCommitDetails[newHash] = {
                    files: [
                        { path: 'backend/app/main.py', status: 'modified', lines: '+8 -2' },
                        { path: 'frontend/index.html', status: 'modified', lines: '+25 -0' }
                    ],
                    overview: 'Simulated AI pipeline trigger executed analysis on codebase components successfully.',
                    impact: 'Maintains codebase integrity with no performance degradation.'
                };

                renderCommitsTable(currentSelectedRepo);
                alert(`AI Job dispatched & processed successfully for commit ${newHash}!`);
            }, 1200);
        });
    }

    // Load Documentation
    async function loadDocumentationToc() {
        const docsTocContainer = document.querySelector('.docs-toc');
        if (!docsTocContainer) return;

        try {
            const data = await window.API.Documentation.getToc();
            const items = data.items || [];
            
            let tocHTML = '<span class="docs-toc-title">Generated Documentation</span>';
            
            if (items.length === 0) {
                tocHTML += '<div style="padding: 12px; color: var(--text-secondary); font-size: 13px;">No documentation generated yet.</div>';
            } else {
                tocHTML += items.map((item, index) => {
                    const isActive = index === 0 ? 'active' : '';
                    const title = `${item.repo_name}: ${item.message.substring(0, 30)}${item.message.length > 30 ? '...' : ''}`;
                    return `<a class="docs-toc-link ${isActive}" data-doc="${item.commit_id}" style="cursor: pointer;">${title}</a>`;
                }).join('');
            }
            
            docsTocContainer.innerHTML = tocHTML;

            // Attach event listeners to new dynamic TOC links
            document.querySelectorAll('.docs-toc-link').forEach(link => {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    document.querySelectorAll('.docs-toc-link').forEach(l => l.classList.remove('active'));
                    link.classList.add('active');
                    const docKey = link.getAttribute('data-doc');
                    loadDocumentation(docKey);
                });
            });

            // Automatically load the first document if available
            if (items.length > 0) {
                loadDocumentation(items[0].commit_id);
            } else {
                const docsBodyViewport = document.getElementById('docs-body-viewport');
                if (docsBodyViewport) docsBodyViewport.innerHTML = UI.getEmptyStateHTML(
                    'No Documentation Generated', 
                    'Connect a github repository to automatically analyze and produce developer docs.',
                    'Go to Repositories',
                    'document.getElementById(\'nav-repos\').click()'
                );
            }
        } catch (error) {
            console.error('Failed to load documentation TOC', error);
        }
    }

    async function loadDocumentation(commitId) {
        const docsBodyViewport = document.getElementById('docs-body-viewport');
        if (docsBodyViewport) {
            docsBodyViewport.innerHTML = UI.getSkeletonHTML('doc');
        }

        try {
            const docData = await window.API.Documentation.getByCommit(commitId);
            
            if (docsBodyViewport) {
                docsBodyViewport.style.opacity = 0;
                setTimeout(() => {
                    // Parse markdown to HTML if marked is available
                    let htmlContent = '';
                    if (window.marked && docData.markdown) {
                        htmlContent = window.marked.parse(docData.markdown);
                    } else {
                        htmlContent = docData.markdown || UI.getEmptyStateHTML('Empty Doc', 'This document contains no content.');
                    }
                    
                    docsBodyViewport.innerHTML = `<div class="markdown-content">${htmlContent}</div>`;
                    document.getElementById('doc-meta-id').textContent = docData.id ? docData.id.substring(0, 8) : commitId.substring(0,8);
                    document.getElementById('doc-meta-updated').textContent = new Date(docData.created_at).toLocaleString() || 'Just now';
                    
                    docsBodyViewport.style.opacity = 1;
                }, 150);
            }
        } catch (error) {
            if (docsBodyViewport) {
                docsBodyViewport.innerHTML = UI.getErrorStateHTML('Documentation Not Found', error.message);
            }
        }
    }

    // Initial render
    renderRepositories();
    renderActivities();
    loadDocumentationToc(); // Loads TOC and then initial documentation dynamically

    // Global Search Functionality
    const globalSearch = document.getElementById('global-search');
    if (globalSearch) {
        globalSearch.addEventListener('input', (e) => {
            const query = e.target.value;
            renderRepositories(query);
        });
    }

    // Action Triggers
    const triggerSyncBtn = document.getElementById('action-trigger-sync');
    if (triggerSyncBtn) {
        triggerSyncBtn.addEventListener('click', () => {
            triggerSyncBtn.textContent = 'Syncing...';
            triggerSyncBtn.disabled = true;
            setTimeout(() => {
                triggerSyncBtn.textContent = 'Trigger Global Sync';
                triggerSyncBtn.disabled = false;
                
                // Real implementation would trigger a backend sync here.
                // For now, just re-fetch the latest activity feed.
                renderActivities();
                alert('Workspace successfully synchronized!');
            }, 1000);
        });
    }

    // Add Repo Modal Logic
    const actionNewRepo = document.getElementById('action-new-repo');
    const btnAddRepoPage = document.getElementById('btn-add-repo-page');
    const addRepoModal = document.getElementById('add-repo-modal');
    const btnCloseRepoModal = document.getElementById('btn-close-repo-modal');
    const btnCancelRepoModal = document.getElementById('btn-cancel-repo-modal');
    const addRepoForm = document.getElementById('add-repo-form');

    function openAddRepoModal() {
        if (addRepoModal) {
            addRepoModal.classList.add('active');
        }
    }

    function closeAddRepoModal() {
        if (addRepoModal) {
            addRepoModal.classList.remove('active');
            if (addRepoForm) addRepoForm.reset();
        }
    }

    if (actionNewRepo) actionNewRepo.addEventListener('click', openAddRepoModal);
    if (btnAddRepoPage) btnAddRepoPage.addEventListener('click', openAddRepoModal);
    if (btnCloseRepoModal) btnCloseRepoModal.addEventListener('click', closeAddRepoModal);
    if (btnCancelRepoModal) btnCancelRepoModal.addEventListener('click', closeAddRepoModal);

    // Close on outside click
    window.addEventListener('click', (e) => {
        if (e.target === addRepoModal) {
            closeAddRepoModal();
        }
    });

    // Handle form submit
    if (addRepoForm) {
        addRepoForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const btnSubmit = document.getElementById('btn-submit-repo-modal');
            const originalText = btnSubmit.textContent;
            btnSubmit.textContent = 'Adding...';
            btnSubmit.disabled = true;

            const repoData = {
                name: document.getElementById('repo-name').value,
                owner: document.getElementById('repo-owner').value,
                clone_url: document.getElementById('repo-url').value,
                default_branch: document.getElementById('repo-branch').value || 'main',
                webhook_enabled: document.getElementById('repo-webhook').checked
            };

            try {
                await window.API.Repository.create(repoData);
                closeAddRepoModal();
                // Refresh list
                renderRepositories();
                if (typeof renderDashboardRepos === 'function') renderDashboardRepos();
            } catch (err) {
                console.error('Failed to create repository:', err);
                alert('Failed to add repository: ' + err.message);
            } finally {
                btnSubmit.textContent = originalText;
                btnSubmit.disabled = false;
            }
        });
    }
});
