var angular = require("angular");
var uiRouter = require("angular-ui-router");
var measurementListComponent = require("./measurement-list.component");

var measurementListModule = angular.module("measurementList", [
  uiRouter
])
.config(function($stateProvider, $urlRouterProvider){

  $stateProvider.state('measurement-list', {
    url: '/measurement',
    template: '<measurement-list></measurement-list>'
  });

})
.component("measurementList", measurementListComponent)
.name;

module.exports = measurementListModule;
