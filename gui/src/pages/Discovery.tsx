import React from 'react';
import { Search } from 'lucide-react';
import PlaceholderPage from './PlaceholderPage';

const Discovery: React.FC = () => {
    return (
        <PlaceholderPage
            title="Network Discovery"
            icon={Search}
            description="Automated scanning and device onboarding. Define discovery rules and actions to automatically grow your monitored inventory."
        />
    );
};

export default Discovery;
