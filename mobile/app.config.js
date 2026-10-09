// The shared @brucie APK predates the league-owned EAS project. Updates must
// target the project embedded in that binary, without changing new builds.
module.exports = ({config}) => {
  const target = process.env.FLAGTASTIC_UPDATE_TARGET;
  if (!target) return config;
  if (target !== 'legacy-apk') throw new Error('Unknown FLAGTASTIC_UPDATE_TARGET');
  const projectId = '6d0704a1-3b9a-4e30-a4fc-1005afac5140';
  return {
    ...config,
    owner: 'brucie',
    extra: {...config.extra, eas: {...config.extra?.eas, projectId}},
    updates: {...config.updates, url: `https://u.expo.dev/${projectId}`},
  };
};
