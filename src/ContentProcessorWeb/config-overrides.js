const { override, addWebpackModuleRule, addWebpackResolve } = require('customize-cra');

module.exports = override(
  addWebpackModuleRule({
    test: /\.md$/,
    use: 'raw-loader',
  }),
  addWebpackResolve({
    extensions: ['.ts', '.tsx', '.js', '.jsx'],
  }),
);
