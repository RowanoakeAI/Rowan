import React from 'react';
import Navigation from './Navigation';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    return (
        <div className="layout">
            <header>
                <h1>Rowan Documentation</h1>
            </header>
            <Navigation />
            <main>{children}</main>
            <footer>
                <p>&copy; {new Date().getFullYear()} Rowan AI Assistant. All rights reserved.</p>
            </footer>
        </div>
    );
};

export default Layout;