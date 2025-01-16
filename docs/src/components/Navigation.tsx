// Navigation.tsx
import React from 'react';
import { Link } from 'react-router-dom';

const Navigation: React.FC = () => {
    return (
        <nav>
            <ul>
                <li><Link to="/installation">Installation</Link></li>
                <li><Link to="/modules">Modules</Link></li>
                <li><Link to="/configuration">Configuration</Link></li>
                <li><Link to="/api">API</Link></li>
            </ul>
        </nav>
    );
};

export default Navigation;