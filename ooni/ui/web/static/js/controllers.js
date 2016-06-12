;(function() {

  angular
    .module('ooniprobe')
    .controller('MainCtrl', MainCtrl);


  MainCtrl.$inject = ['$scope'];

  function MainCtrl($scope) {
  }


  angular
    .module('ooniprobe')
    .controller('NetTestCtrl', NetTestCtrl);


  NetTestCtrl.$inject = ['$scope', '$http', '$routeParams', '$window'];

  function NetTestCtrl($scope, $http, $routeParams, $window) {
    $http.get('/net-tests')
      .then(function(response){
        $scope.netTests = response.data;
        if ($routeParams.testName) {
          $scope.runNetTest($routeParams.testName);
        }
      }, function(error){
        console.log(error);
      });

    $scope.runNetTest = function(testName) {
      if ($scope.netTests[testName]) {
        $scope.selectedNetTest = $scope.netTests[testName];
        $window.scrollTo(0, 0);
      }
    }

    $scope.startNetTest = function() {
      var options = {};
      $window.scrollTo(0, 0);
      angular.forEach($scope.selectedNetTest.arguments, function(value, key) {
        if (value.value != null) {
          options[key] = ''+value.value;
        } else {
          options[key] = value.value;
        }
      });

      console.log(options);
      $http
        .post(
          '/net-tests/'+$scope.selectedNetTest.id+'/start',
           options
        )
        .then(function(response){
          console.log(response);
        }, function(error){

        });
    }

  }


})();
