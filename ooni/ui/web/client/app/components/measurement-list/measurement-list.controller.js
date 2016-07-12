function MeasurementListController($stateParams, $scope, $http,  $window) {
   $http.get('/api/measurement')
    .then(function(response){
      $scope.measurements = response.data['measurements'];
    }, function(error){
      console.log(error);
    });

}
MeasurementListController.$inject = ['$stateParams', '$scope', '$http', '$window'];
module.exports = MeasurementListController;
