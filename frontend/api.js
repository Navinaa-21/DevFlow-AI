/**
 * Centralized API Service for DevFlow AI
 * Uses Axios for HTTP requests, configured with base URL,
 * interceptors, and error handling.
 */

const API_BASE_URL = window.ENV?.API_URL || window.location.origin;

// Configure Axios Instance
const apiClient = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json'
    }
});

// Request Interceptor
apiClient.interceptors.request.use(
    (config) => {
        const token = window.Auth ? window.Auth.getToken() : localStorage.getItem('devflow_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response Interceptor
apiClient.interceptors.response.use(
    (response) => {
        return response.data;
    },
    (error) => {
        // Centralized Error Handling
        console.error('API Error:', error);
        
        if (error.response && error.response.status === 401) {
            if (window.Auth) window.Auth.logout();
        }
        
        let errorMsg = 'An unexpected error occurred. Please try again.';
        if (error.response) {
            // The request was made and the server responded with a status code
            if (error.response.status === 404) {
                errorMsg = 'The requested resource was not found on the server.';
            } else if (error.response.status === 500) {
                errorMsg = 'Internal Server Error. Please contact support.';
            } else if (error.response.data && error.response.data.detail) {
                errorMsg = error.response.data.detail;
            }
        } else if (error.request) {
            // The request was made but no response was received
            errorMsg = 'Network error. Could not connect to the server.';
        }
        
        return Promise.reject(new Error(errorMsg));
    }
);

// --- API Feature Modules ---

window.API = {
    // Endpoints currently used by the UI (Mocked/Future Backend implementation)
    Dashboard: {
        getStats: () => apiClient.get('/dashboard/stats')
    },
    
    Repository: {
        getAll: () => apiClient.get('/repositories/'),
        getDetails: (repoName) => apiClient.get(`/repositories/${repoName}`),
        create: (data) => apiClient.post('/repositories/', data)
    },
    
    Github: {
        getAvailable: () => apiClient.get('/api/v1/github/repositories'),
        connect: (githubRepoId) => apiClient.post(`/api/v1/github/connect/${githubRepoId}`),
        disconnect: (repositoryId) => apiClient.delete(`/api/v1/github/disconnect/${repositoryId}`)
    },
    
    Activity: {
        getFeed: () => apiClient.get('/activity/')
    },
    
    // Actual FastAPI Backend Endpoints
    System: {
        checkHealth: () => apiClient.get('/health')
    },

    Webhooks: {
        triggerGithub: (payload, signature) => apiClient.post('/webhooks/github', payload, {
            headers: {
                'x-hub-signature-256': signature
            }
        })
    },
    
    Commits: {
        // UI specific endpoints
        getByRepo: (repoName) => apiClient.get(`/commits/repo/${repoName}`),
        
        // FastAPI endpoints
        list: (skip = 0, limit = 100) => apiClient.get('/commits/', { params: { skip, limit } }),
        getDetails: (commitId) => apiClient.get(`/commits/${commitId}`)
    },
    
    Documentation: {
        // UI specific endpoints
        getToc: () => apiClient.get('/documentation/toc'),
        getPage: (docKey) => apiClient.get(`/documentation/${docKey}`),

        getByCommit: (commitId) => apiClient.get(`/documentation/commits/${commitId}/documentation`)
    }
};
