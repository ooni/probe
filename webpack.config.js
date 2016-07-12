var fs = require('fs');
var path = require('path');

var webpack = require('webpack');
var HtmlWebpackPlugin = require('html-webpack-plugin');

var node_env = process.env.NODE_ENV || 'development';

var context = path.join(__dirname);

var rootWebPath = "./ooni/ui/web/";
var contextRoot = path.join(context, rootWebPath);

module.exports = {
  entry: {
    app: [path.join(contextRoot, "client", "app", "app.js")]
  },
  output: {
    path: path.join(contextRoot, "build"),
    filename: "[name].bundle.js"
  },
  module: {
    loaders: [
      { test: /\.js$/, exclude: [/node_modules/], loader: 'ng-annotate'  },
      { test: /\.html$/, loader: 'raw' },
      { test: /\.css$/, loader: 'style-loader!css-loader' },
      { test: /\.eot(\?v=\d+\.\d+\.\d+)?$/, loader: "file" },
			{ test: /\.(woff|woff2)$/, loader:"url?prefix=font/&limit=5000" },
			{ test: /\.ttf(\?v=\d+\.\d+\.\d+)?$/, loader: "url?limit=10000&mimetype=application/octet-stream" },
			{ test: /\.svg(\?v=\d+\.\d+\.\d+)?$/, loader: "url?limit=10000&mimetype=image/svg+xml" }

    ]
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: path.join(rootWebPath, 'client', 'index.html'),
      inject: 'body',
      hash: true
    })
  ]

}
