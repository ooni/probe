'use strict';

angular.module('ooniprobe.services', ['ngResource']).
  factory('listTests', ['$resource',
          function($resource) {
    return $resource('/test');
}]).
  factory('testStatus', ['$http', function($http){
    return function(testID) {
      return $http.get('/test/' + testID);
    }
}]).
  factory('startTest', ['$http',
          function($http) {
    return function(testID, options) {
      return $http.post('/test/' + testID + '/start', options);
    }
}]).
  factory('Inputs', ['$resource',
          function($resource) {
    return $resource('/inputs');
}]).
  factory('status', ['$resource',
    function($resource) {
    return $resource('/status');
}]);

