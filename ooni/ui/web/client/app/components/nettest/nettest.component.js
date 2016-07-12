var template = require("./nettest.html");
var controller = require("./nettest.controller");
require("./nettest.css");

module.exports = {
  restrict: 'E',
  bindings: {},
  template: template,
  controller: controller
};
