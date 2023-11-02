import { createRouter, createWebHistory } from 'vue-router'
import ListView from "@/views/ListView.vue";
import ImageView from "@/views/ImageView.vue";
import ListCollectionView from "@/views/ListCollectionView.vue"

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/:uuid([0-9a-f:]{20,})',
      name: 'image',
      component: ImageView,
      props: (route) => ({
        uuid: route.params['uuid']
      }),
    },
    {
      path: '/collections/',
      name: 'collections',
      component: ListCollectionView,
    },
    {
      path: '/collections/:collection([^/:]*)/',
      name: 'images',
      component: ListView,
      props: (route) => ({
        collection: route.params['collection']
      }),
    },
    {
      path: '/',
      name: 'index',
      component: ListView,
      props: () => ({
        collection: '@'
      }),
    },
  ],
})

export default router
