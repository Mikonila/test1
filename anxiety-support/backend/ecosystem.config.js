module.exports = {
  apps: [
    {
      name: 'anxiety-support-backend',
      script: './server.js',
      cwd: '/opt/anxiety-support/backend',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      env: {
        NODE_ENV: 'production',
        PORT: 3000,
      },
    },
  ],
};
