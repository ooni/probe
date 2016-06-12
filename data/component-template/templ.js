var angular = require("angular");
var uiRouter = require("angular-ui-router");
var {{name}}Component = require("./{{name}}.component");

var {{name}}Module = angular.module("{{name}}", [
  uiRouter
])
.config(function($stateProvider, $urlRouterProvider){

  $stateProvider.state('{{name}}', {
    url: '/{{name}}',
    template: '<{{name}}></{{name}}>'
  });

})
.component("{{name}}", {{name}}Component)
.name;

module.exports = {{name}}Module;
