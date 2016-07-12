var angular = require("angular");
var uiRouter = require("angular-ui-router");
var measurementComponent = require("./measurement.component");

var measurementModule = angular.module("measurement", [
  uiRouter
])
.config(function($stateProvider, $urlRouterProvider){

  $stateProvider.state('measurement', {
    url: '/measurement/:measurementId/:idx',
    template: '<measurement></measurement>'
  });

})
.component("measurement", measurementComponent)
.name;

module.exports = measurementModule;
