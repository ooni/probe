var angular = require("angular");
var Nettest = require("./nettest/nettest")

var componentsModule = angular.module("app.components", [
  Nettest
])
.name;

module.exports = componentsModule;
