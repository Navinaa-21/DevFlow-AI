/**
 * Centralized Authentication Context
 */

window.Auth = {
    isAuthenticated: false,
    currentUser: null,
    
    getToken: () => {
        return localStorage.getItem('devflow_token');
    },
    
    setToken: (token) => {
        localStorage.setItem('devflow_token', token);
    },
    
    login: () => {
        window.location.href = (window.ENV?.API_URL || window.location.origin) + '/api/v1/auth/github/login';
    },
    
    logout: () => {
        localStorage.removeItem('devflow_token');
        window.Auth.isAuthenticated = false;
        window.Auth.currentUser = null;
        window.location.href = '/'; // Trigger reload to show login screen
    },
    
    init: async () => {
        // Check for token in URL
        const urlParams = new URLSearchParams(window.location.search);
        const urlToken = urlParams.get('token');
        
        if (urlToken) {
            window.Auth.setToken(urlToken);
            // Clean URL
            window.history.replaceState({}, document.title, '/');
        }
        
        const token = window.Auth.getToken();
        if (!token) {
            return false; // Not authenticated
        }
        
        // Verify token with backend
        try {
            const baseUrl = window.ENV?.API_URL || window.location.origin;
            const response = await fetch(`${baseUrl}/api/v1/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/json'
                }
            });
            
            if (response.ok) {
                const user = await response.json();
                window.Auth.isAuthenticated = true;
                window.Auth.currentUser = user;
                return true;
            } else {
                window.Auth.logout();
                return false;
            }
        } catch (error) {
            console.error("Auth validation failed", error);
            window.Auth.logout();
            return false;
        }
    }
};
