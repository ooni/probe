var angular = require("angular");
var uiRouter = require("angular-ui-router");
var measurementSummaryComponent = require("./measurement-summary.component");

var measurementSummaryModule = angular.module("measurementSummary", [
  uiRouter
])
.config(function($stateProvider, $urlRouterProvider){

  $stateProvider.state('measurement-summary', {
    url: '/measurement/:measurementId',
    template: '<measurement-summary></measurement-summary>'
  });

})
.component("measurementSummary", measurementSummaryComponent)
.name;

module.exports = measurementSummaryModule;
