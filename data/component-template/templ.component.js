var template = require("./{{name}}.html");
var controller = require("./{{name}}.controller");
require("./{{name}}.css");

module.exports = {
  restrict: 'E',
  bindings: {},
  template: template,
  controller: controller
};
