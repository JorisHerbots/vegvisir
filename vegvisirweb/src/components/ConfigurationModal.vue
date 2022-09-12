
<template>


<!-- Main modal -->
<div id="configurationModal" @keydown.esc="Accept" tabindex="-1" aria-hidden="true" class="overflow-y-auto overflow-x-hidden fixed top-0 right-0 left-0 z-50 w-full md:inset-0 h-modal md:h-full">
    <div class="relative p-4 w-full md:h-auto">
        <!-- Modal content -->
        <div id="test" class="relative bg-white rounded-lg shadow dark:bg-gray-700">
            <!-- Modal header -->
            <div class="flex justify-between items-start p-4 rounded-t border-b dark:border-gray-600">
                <h3 class="text-xl font-semibold text-gray-900 dark:text-white">
                    Configuration of: {{ActiveImplementation["url"]}}
                </h3>
                <button type="button" @click="Accept" class="text-gray-400 bg-transparent hover:bg-gray-200 hover:text-gray-900 rounded-lg text-sm p-1.5 ml-auto inline-flex items-center dark:hover:bg-gray-600 dark:hover:text-white" data-modal-toggle="defaultModal">
                    <svg aria-hidden="true" class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path></svg>
                    <span class="sr-only">Close modal</span>
                </button>
            </div>
            <!-- Modal body -->
            <div class="p-6 space-y-1">

          <div v-if="showError">
            <div id="alert" class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded z-40" role="alert">
              <strong class="font-bold">Error</strong>
              <span class="block sm:inline ml-4">{{errorMessage}}</span>
              <span class="absolute top-0 bottom-0 right-0 px-4 py-3">
                <svg @click="showError = false;" class="fill-current h-6 w-6 text-red-500" role="button" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><title>Close</title><path d="M14.348 14.849a1.2 1.2 0 0 1-1.697 0L10 11.819l-2.651 3.029a1.2 1.2 0 1 1-1.697-1.697l2.758-3.15-2.759-3.152a1.2 1.2 0 1 1 1.697-1.697L10 8.183l2.651-3.031a1.2 1.2 0 1 1 1.697 1.697l-2.758 3.152 2.758 3.15a1.2 1.2 0 0 1 0 1.698z"/></svg>
              </span>
            </div>
          </div>

                <p class="text-base leading-relaxed text-gray-500 dark:text-gray-400">

                  <div v-if="'env' in ActiveImplementation">
                      <li  v-for="(item, index) in ActiveImplementation['env']">
                        <div v-if="'type' in item && item.type === 'dropdown'">         
                          {{item.name}}                  
                          
                          <div v-if="CanBeModified">
                          <select class="bg-gray-200  border-2 border-gray-200 rounded w-full py-2 px-4 text-gray-700 leading-tight focus:outline-none focus:bg-white focus:border-teal-500" name="temp">
                            
                            <option  v-for="(item2, index2) in item.options" value="item2">{{item2}}</option>
                          </select>
                          </div>

                          <div v-if="!CanBeModified">
                            <select class="bg-gray-200  border-2 border-gray-200 rounded w-full py-2 px-4 text-gray-700 leading-tight focus:outline-none focus:bg-white focus:border-teal-500" disabled name="temp">
                              
                              <option  v-for="(item2, index2) in item.options" value="item2">{{item2}}</option>
                            </select>
                          </div>


                        </div>
                        
                        <div v-if="!('type' in item) || item.type !== 'dropdown'">  
                          {{item.name}} 
                          <div v-if="CanBeModified">
                            <input class="bg-gray-200 appearance-none border-2 border-gray-200 rounded w-full py-2 px-4 text-gray-700 leading-tight focus:outline-none focus:bg-white focus:border-teal-500" id="inline-full-name" type="text" v-model="item.value" :placeholder="item.default">
                          </div>

                          <div v-if="!CanBeModified">
                            <input class="bg-gray-200 appearance-none border-2 border-gray-200 rounded w-full py-2 px-4 text-gray-700 leading-tight focus:outline-none focus:bg-white focus:border-teal-500" id="inline-full-name" type="text" v-model="item.value" :placeholder="item.default" readonly>
                          </div>
                        </div>


                      </li> 
                  </div>
                  <div v-if="!('env' in ActiveImplementation)">
                      Nothing to configure
                  </div>

                  <div v-if="'scenarios' in ActiveImplementation">
                      <li  v-for="(item, index) in ActiveImplementation['scenarios']">
                          {{index}} 
                           <div v-if="CanBeModified">
                            <input class="bg-gray-200 appearance-none border-2 border-gray-200 rounded w-full py-2 px-4 text-gray-700 leading-tight focus:outline-none focus:bg-white focus:border-teal-500" id="inline-full-name" type="text" v-model="item.value" :placeholder="item.arguments">
                          </div>

                          <div v-if="!CanBeModified">
                            <input class="bg-gray-200 appearance-none border-2 border-gray-200 rounded w-full py-2 px-4 text-gray-700 leading-tight focus:outline-none focus:bg-white focus:border-teal-500" id="inline-full-name" type="text" v-model="item.value" :placeholder="item.arguments" readonly>
                          </div>
                      </li> 
                  </div>
                </p>

            </div>
            <!-- Modal footer -->
            <div id="test2" class="absolute right-0 flex items-center p-6 space-x-2 rounded-b border-gray-200 dark:border-gray-600">
                <button data-modal-toggle="defaultModal" type="button" @click="Accept" class="text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800">OK</button>
            </div>
        </div>
    </div>
</div>


</template>


<script lang="ts">
export default {
  props: {
    ActiveImplementation: {},
    CanBeModified: false
  },

  data: () => ({
    showError: false,
    errorMessage: String
  }),
  methods: {
    Accept() {
      if (!this.CheckErrors())
        this.$emit("accept", true);
    },
    CheckErrors() {
      if (!this.CanBeModified) {
        return false;
      }

      for (let item in this.ActiveImplementation["env"]) {

        item = this.ActiveImplementation["env"][item];
        if (item.hasOwnProperty("type")) {
          // dropdown 
          if (item.type == "dropdown") {
            // User can't do anything wrong
          }
          if (item.type == "") {
            // Assume input can't be empty
            if (item.value === "") {
              //error
              this.errorMessage = "Value of configurable property " + item.name + " can't be empty!";
              this.showError = true;
              return true;
            }
          }
        }
        else {
          if (item.value == "") {
            //error
              this.errorMessage = "Value of configurable property " + item.name + " can't be empty!";
              this.showError = true;
              return true;
          }          
        }
      }

      return false;
    }
  },
  mounted(this: ComponentPublicInstance): void {
     document.getElementById("configurationModal").focus();
  }
};
</script>

<style>

.card {
}

#test {
  height: 95vh;
}

#test2 {
  bottom: 0px;
} 

</style>