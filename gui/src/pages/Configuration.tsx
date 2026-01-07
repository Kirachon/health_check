import React from 'react';
import { Settings } from 'lucide-react';
import PlaceholderPage from './PlaceholderPage';

const Configuration: React.FC = () => {
    return (
        <PlaceholderPage
            title="Global Configuration"
            icon={Settings}
            description="Manage users, templates, roles, and global monitoring intervals. Fine-tune your Zabbix-grade health monitoring system settings."
        />
    );
};

export default Configuration;
