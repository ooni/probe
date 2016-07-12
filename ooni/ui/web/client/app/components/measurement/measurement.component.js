var template = require("./measurement.html");
var controller = require("./measurement.controller");
require("./measurement.css");

module.exports = {
  restrict: 'E',
  bindings: {},
  template: template,
  controller: controller
};
