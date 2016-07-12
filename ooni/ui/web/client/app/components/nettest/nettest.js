var angular = require("angular");
var uiRouter = require("angular-ui-router");
var nettestComponent = require("./nettest.component");

var nettestModule = angular.module("nettest", [
  uiRouter
])
.config(function($stateProvider, $urlRouterProvider){

  $urlRouterProvider.otherwise('/');

  $stateProvider.state('nettest', {
    url: '/nettest/:testName?',
    template: '<nettest></nettest>'
  });

})
.component("nettest", nettestComponent)
.name;

module.exports = nettestModule;
