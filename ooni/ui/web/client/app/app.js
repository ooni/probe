var angular = require('angular');
var uiRouter = require('angular-ui-router');
var Common = require('./common/common');
var Components = require('./components/components');
var AppComponent = require('./app.component');
require('normalize.css');
require('bootstrap/dist/css/bootstrap.css');

angular.module('app', [
    uiRouter,
    Common,
    Components
  ])
  .component('app', AppComponent);
